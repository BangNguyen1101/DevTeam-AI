# Thiết kế AI Agent

> Trạng thái: **đã triển khai** (`backend/app/ai_core/`). Đã kiểm thử end-to-end với model giả lập; chạy với LLM thật cần `LLM_API_KEY`.

## 1. Nguyên tắc

1. **LLM quyết định nội dung, code quyết định luồng.** AI Manager (LLM) lập kế hoạch; `WorkflowEngine` (Python) thực thi DAG, giới hạn và ghi lại mọi thứ.
2. **Output có cấu trúc, không tool calling.** Mỗi agent trả về một model Pydantic (`output_type` của OpenAI Agents SDK, schema non-strict). Engine mới là bên ghi file và chạy lệnh. Nhờ vậy quyền được kiểm soát tập trung, số lượt gọi ít và chạy được với model nhỏ/free tier.
3. **Quyền tối thiểu.** `agent_permissions` (`fs.write:<area>`) quyết định thư mục agent được ghi. Engine kiểm tra mọi đường dẫn trước khi ghi (all-or-nothing).
4. **Mọi lần gọi đều được ghi lại**: `llm_usage`, `execution_events`, `artifacts`, `command_executions`.

## 2. Nhà cung cấp LLM

- `app/ai_core/llm/provider.py`: `AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)` + `OpenAIChatCompletionsModel`. Mọi endpoint tương thích OpenAI Chat Completions đều dùng được.
- Môi trường phát triển: **Gemini API free tier** (`https://generativelanguage.googleapis.com/v1beta/openai/`). Muốn dùng OpenAI thì để trống `LLM_BASE_URL`.
- Tracing của SDK bị tắt (không gửi prompt lên OpenAI platform); lịch sử nằm trong SQL Server.
- `GET /api/v1/llm/models` liệt kê model của nhà cung cấp để chọn trong Cài đặt.

## 3. Luồng một Run

```
POST /projects/{id}/runs {request_text, budget_usd?}
 └─ run: pending → planning
 └─ Manager → Plan{analysis, tasks[key, agent_code, title, description, depends_on]}
      validate_plan: agent tồn tại & bật, key hợp lệ/duy nhất, có BA + Architect,
      mỗi agent ≤ 1 task, không chu trình. Sai → gọi lại kèm danh sách lỗi (≤ max_task_attempts)
 └─ run: running. Lặp:
      task sẵn sàng = pending + mọi phụ thuộc completed → chạy song song (asyncio.TaskGroup)
      phụ thuộc failed/skipped → task skipped
      mỗi task: kiểm tra ngân sách → gọi agent → ghi file/artifact → completed
                lỗi (LLM, schema, quyền ghi) → thử lại tới max_attempts → failed
 └─ QA: viết tests/ → chạy pytest (cần phê duyệt) → report
      lỗi → engine thêm task fix_N (code_reviewer) + retest_N (qa_tester) vào DAG
      vượt max_fix_iterations → run failed
 └─ Lần đầu test đạt → task `review` (code_reviewer, bắt buộc, tắt được trong Cài đặt):
      quét tĩnh (static_checks) → findings bắt buộc sửa trong prompt → LLM review → quét lại
      còn findings → thử lại kèm danh sách còn lại; hết lượt → ghi "CHƯA XỬ LÝ" + sự kiện security.unresolved
      reviewer sửa file → task `retest_review` (qa_tester)
 └─ Manager tổng hợp (RunSummary) → run completed
Hủy: POST /runs/{id}/cancel → engine dừng ở bước kế tiếp. Backend khởi động lại → run dở dang được đánh dấu failed.
```

## 4. Agent

| Agent | Đầu vào | Output | Engine làm gì |
|---|---|---|---|
| Manager | Yêu cầu | `Plan`, `RunSummary` | Tạo task + phụ thuộc; lưu artifact `plan`; ghi `summary` |
| Business Analyst | Yêu cầu | `Document` | Ghi `docs/SRS.md`, artifact `requirements` |
| Architect | + SRS | `Document` | Ghi `docs/DESIGN.md`, artifact `design` |
| Backend Dev | + SRS, DESIGN, code `backend/` hiện có | `CodeChangeSet` | Ghi/xóa `backend/**` |
| Frontend Dev | + SRS, DESIGN, code `frontend/` hiện có | `CodeChangeSet` | Ghi/xóa `frontend/**` |
| QA Tester | + tài liệu + code backend | `CodeChangeSet` | Ghi/xóa `tests/**`, chạy pytest, artifact `test_report` |
| Code Reviewer (sửa lỗi) | + report lỗi + code + test | `ReviewResult` | Ghi bản sửa (`backend/`, `frontend/`, `tests/`), artifact `review` |
| Code Reviewer (review bắt buộc) | + code + test + kết quả quét tĩnh | `ReviewResult` | Như trên; engine quét lại sau khi sửa |

Mọi agent đều nhận **danh sách file hiện có** trong workspace. `FileChange.delete=true` cho phép xóa file lỗi thời trong vùng của mình. File ngoài vùng bị bỏ qua và ghi sự kiện `files.rejected`; đường dẫn thoát workspace bị chặn cả change set.

Chỉ dẫn mặc định ở `app/ai_core/agents/prompts.py` (kèm "hợp đồng dự án": FastAPI trong `backend/app/main.py`, dữ liệu in-memory, chỉ dùng stdlib + fastapi + pydantic + httpx + pytest). Cột `agents.instructions` được **nối thêm**, không thay thế.

## 5. Execution Engine

- `app/ai_core/execution/engine.py`: chỉ chạy lệnh có tên trong `ALLOWED_COMMANDS` (hiện chỉ `pytest`), `shell=False`, `cwd` = workspace, timeout `limits.command_timeout_seconds`, stdout/stderr cắt còn 20.000 ký tự.
- Môi trường con tối thiểu: chỉ `PATH/SYSTEMROOT/TEMP…` + `PYTHONPATH=<workspace>/backend`; **không** có `LLM_API_KEY`, chuỗi kết nối DB.
- `limits.require_command_approval` (mặc định bật): trước mỗi lần chạy test, engine tạo `approvals` (kind `command`), run/task chuyển `waiting_approval`, chờ người dùng duyệt (hết hạn sau 1 giờ). Từ chối → run failed.
- **Hạn chế đã biết:** code do AI sinh ra chạy trực tiếp trên máy với quyền của tài khoản chạy backend (chưa có sandbox/container). Vì vậy bắt buộc phê duyệt là mặc định.
- Run kết thúc/bị hủy → các phê duyệt đang chờ của run đó tự chuyển "rejected" kèm lý do.

### Quét bảo mật tĩnh (`execution/static_checks.py`)
Quét `backend/` và `frontend/` (không phụ thuộc LLM):
- `xss-innerhtml`: mọi phép gán `innerHTML/outerHTML` **trừ** chuỗi tĩnh hoàn toàn (allow-list; deny-list ban đầu bỏ sót `innerHTML = items.map(b => \`${…}\`)` ở run #7)
- `xss-insert-adjacent`, `xss-document-write`, `js-eval`
- `py-eval` (`eval/exec`), `py-shell` (`os.system`, `os.popen`, `subprocess`), `py-pickle`

### Client LLM
`max_retries=0`, timeout 120s; retry/backoff do `call_agent` quản lý (5/15/30/60/90s cho 429/503/timeout). Quota ngày (`PerDay`) → dừng run ngay với thông báo đổi model.

## 6. Chi phí và token

- Sau mỗi lượt gọi: `llm_usage` (input/cached/output tokens, số request, latency) và `cost_usd` tính theo `app_settings.pricing[model]` (USD/1M token do người dùng nhập; model chưa có giá → $0).
- `workflow_runs.total_*` cộng dồn; kiểm tra `budget_usd` trước mỗi task.

## 7. Kiểm thử

`backend/tests/test_engine.py` dùng `FakeModel` (cài đặt interface `Model` của Agents SDK) thay cho LLM. Các thành phần còn lại đều chạy thật: SQL Server, file trong workspace, pytest thật trên code sinh ra. Các kịch bản:
pipeline đầy đủ, vòng fix/retest, hết vòng sửa, agent ghi sai vùng, chờ phê duyệt, từ chối phê duyệt, kế hoạch sai được gọi lại, vượt ngân sách, allowlist + môi trường sạch, API tạo/hủy run.
