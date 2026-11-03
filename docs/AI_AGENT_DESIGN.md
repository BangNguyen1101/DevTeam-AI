# Thiết kế AI Agent

> Trạng thái: **thiết kế**. Dữ liệu agent + quyền đã seed trong DB (tuần 1); phần thực thi triển khai tuần 2–3.

## 1. Nguyên tắc

1. **LLM quyết định nội dung, code quyết định luồng.** Manager (LLM) lập kế hoạch; Workflow Engine (Python) thực thi, giới hạn và ghi lại mọi thứ.
2. **Output có cấu trúc.** Mỗi Agent trả về một model Pydantic (`output_type` của OpenAI Agents SDK) → validate được, lưu được, truyền được cho Agent sau.
3. **Quyền tối thiểu.** Agent chỉ nhận tool tương ứng với `agent_permissions`.
4. **Mọi lần gọi đều được ghi lại**: `llm_usage`, `execution_events`, `artifacts`.

## 2. Luồng một Run

```
POST /projects/{id}/runs {request}
 └─ workflow_runs(status=planning)
 └─ Manager.plan(request) → Plan{tasks:[{key, agent_code, title, description, depends_on[]}]}
      ├─ validate: agent tồn tại & bật, key duy nhất, không chu trình, BA đi trước Architect…
      └─ ghi tasks + task_dependencies
 └─ status=running → Engine loop:
      ready = tasks pending có mọi dependency completed
      chạy song song các task ready (asyncio.gather) – ví dụ Backend ∥ Frontend
      mỗi task:
        context = request + artifacts của các task phụ thuộc (cắt gọn theo ngân sách token)
        result  = Runner.run(agent, context, max_turns)
        lưu artifact(s), output_data, llm_usage, event → WebSocket runs:<id>
        lỗi → attempt+1, retry nếu < max_attempts, ngược lại failed
      QA thất bại → tạo task "fix" cho code_reviewer → task "retest" cho qa_tester
                    (tối đa limits.max_fix_iterations vòng)
      cần phê duyệt → status=waiting_approval, dừng đến khi người dùng quyết định
      vượt ngân sách → dừng, status=failed (error=budget_exceeded)
 └─ Manager.summarize(artifacts, test report) → workflow_runs.summary, status=completed
```

## 3. Agent

| Agent | Đầu vào | Output (Pydantic) | Tool |
|---|---|---|---|
| Manager | Yêu cầu người dùng | `Plan`, `RunSummary` | – |
| Business Analyst | Yêu cầu | `RequirementsSpec` (functional, non-functional, user stories, acceptance criteria) → `docs/SRS.md` | write_file (docs) |
| Architect | SRS | `TechnicalDesign` (stack, cấu trúc thư mục, entities, API endpoints) → `docs/DESIGN.md` | read_file, write_file (docs) |
| Backend Dev | SRS + Design | `CodeChangeSet` (danh sách file + giải thích) | read_file, list_dir, write_file (backend) |
| Frontend Dev | SRS + Design (API contract) | `CodeChangeSet` | read_file, list_dir, write_file (frontend) |
| QA Tester | SRS + Design + code | `TestReport` (test cases, kết quả, lỗi) | read_file, write_file (tests), run_command |
| Code Reviewer | Code + TestReport | `ReviewResult` (issues, fixes đã áp dụng) | read_file, write_file (backend/frontend/tests), run_command |

## 4. Tools và kiểm soát

| Tool | Kiểm soát |
|---|---|
| `read_file`, `list_dir` | `WorkspaceManager.resolve` – chặn `..`, đường dẫn tuyệt đối, UNC; giới hạn kích thước file đọc |
| `write_file(path, content)` | Như trên + kiểm tra vùng ghi theo quyền `fs.write:<area>` (thư mục đầu tiên của path) |
| `run_command(name)` | Chỉ lệnh trong allowlist định danh sẵn (vd. `pytest` → `python -m pytest -q`), `shell=False`, `cwd` trong workspace, timeout `limits.command_timeout_seconds`, env sạch (không có API key), cắt stdout/stderr. Lệnh khác → tạo `approvals` |

## 5. Chi phí và token

- Sau mỗi `Runner.run`, đọc usage (input/cached/output tokens, số request) → `llm_usage` với `cost_usd` tính theo bảng giá trong `app_settings`.
- `workflow_runs.total_*` cộng dồn; kiểm tra `budget_usd` trước mỗi task.
- Model và `max_output_tokens` cấu hình theo từng agent trong bảng `agents`.

## 6. Rủi ro đã lường trước

- **Output không ổn định** → structured output + validate + retry; app demo nhỏ.
- **Vòng lặp vô hạn** → `max_turns` cho mỗi Agent, `max_attempts` cho mỗi task, `max_fix_iterations` cho mỗi run.
- **SDK thay đổi** → ghim phiên bản `openai-agents`; gói SDK sau một adapter mỏng trong `ai_core/agents`.
