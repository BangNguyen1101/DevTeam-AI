# Tiến độ dự án

> Từ 2026-11-03 dự án không chia theo tuần nữa; tiến độ ghi theo từng mốc chức năng.

## Review bắt buộc + quét bảo mật tĩnh + hỗ trợ cải tiến lặp · ✅ code & test (2026-11-03)

### Đã làm
| Hạng mục | Chi tiết |
|---|---|
| Review bắt buộc | Lần đầu test đạt → task `review` (Code Reviewer, checklist bảo mật/nghiệp vụ/xử lý lỗi); sửa file → `retest_review`. Công tắc trong Cài đặt (mặc định bật) |
| Quét tĩnh | `static_checks.py` chạy trước/sau review; còn lỗi → thử lại kèm danh sách; hết lượt → "CHƯA XỬ LÝ" + `security.unresolved` |
| Cải tiến lặp | Agent thấy danh sách file hiện có; Dev agent thấy code hiện có của vùng mình; `FileChange.delete` để xóa file lỗi thời |
| Ổn định | Client LLM không tự retry (timeout 120s); hủy/thất bại run tự đóng phê duyệt đang chờ |

`pytest`: **63/63**.

### Chạy thật (dự án "Quản lý thư viện")
| Run | Yêu cầu | Kết quả | Phát hiện → sửa |
|---|---|---|---|
| #6 | Làm lại từ đầu | ✅ 10 task, 2 vòng fix, 14 test đạt | Test cũ của run #5 còn sót → agent được xóa file; review LLM nêu XSS nhưng không sửa → thêm quét tĩnh |
| #7 | Cải tiến: lỗi trả sách chưa mượn, validate rỗng, hiển thị lỗi | ✅ 11 task, 2 vòng fix (422→400), review sửa 2 file, retest đạt, 10 test | Quét tĩnh bản đầu bỏ sót `innerHTML = books.map(...)` → đổi sang allow-list |
| #8 | Thêm thống kê | ❌ đã hủy | Frontend Dev viết lại app.js từ đầu, mất danh sách/mượn/trả (không thấy code hiện có) → Dev agent nhận code vùng của mình; phê duyệt treo sau khi hủy → tự đóng |
| #9 | Khôi phục trang web đầy đủ + thống kê | ✅ 7 task, test đạt, quét tĩnh phát hiện XSS → review sửa ngay lần đầu (createElement + textContent) → retest đạt | Không còn file bị từ chối nhờ Dev agent thấy code hiện có |

### Chạy thử ứng dụng do đội AI tạo (sau run #9)
`library-api` (uvicorn :8001) + `library-web` (http.server :8002) trong `.claude/launch.json`, thao tác trên trình duyệt:

| Kịch bản | Kết quả |
|---|---|
| Trang tải: thống kê, form, bảng sách, nút Mượn/Trả | ✅ không lỗi console |
| Thêm sách tên rỗng | ✅ hiện "Tiêu đề và tác giả không được để trống" (400) |
| Thêm sách tên `<img src=x onerror=alert('XSS')>` | ✅ hiển thị dạng chữ, 0 alert, 0 thẻ img → XSS đã chặn |
| Mượn sách 1 / trả sách 2 qua UI | ✅ trạng thái và thống kê cập nhật |
| API: mượn sách đang mượn / trả sách chưa mượn | ✅ 400 kèm thông báo tiếng Việt |

### Hạn chế còn lại
- Workspace chưa có lịch sử phiên bản: run #8 ghi đè frontend tốt. Nên snapshot/git trong workspace trước mỗi run.
- QA chỉ kiểm thử backend; frontend chỉ được quét tĩnh.

## Chạy thật với Gemini · ✅ (2026-11-03)

Yêu cầu (dự án "Quản lý thư viện", run #5): *API quản lý thư viện nhỏ: thêm sách, xem danh sách, mượn/trả, không cho mượn sách đang được mượn; kèm trang web đơn giản.*

| Bước | Agent / model | Thời gian | Kết quả |
|---|---|---|---|
| Lập kế hoạch | Manager / gemini-3.1-flash-lite | 3s | 5 task: BA → Architect → Backend ∥ Frontend → QA |
| Đặc tả | BA / gemini-flash-lite-latest | 15s | `docs/SRS.md` |
| Thiết kế | Architect / gemini-3.5-flash-lite | 12s | `docs/DESIGN.md` |
| Code (song song) | Backend / gemini-3.5-flash-lite, Frontend / gemini-3.1-flash-lite | 21s | `backend/app/main.py` (4 endpoint), `frontend/index.html, app.js, styles.css`; 7 file ngoài vùng của backend bị bỏ qua |
| Kiểm thử | QA / gemini-flash-lite-latest | 5s + chờ duyệt | `tests/test_main.py`, sau khi phê duyệt: **pytest 7 passed** (exit 0, 1,2s) |
| Tổng hợp | Manager | 2s | Bản tóm tắt Markdown hiển thị trong Không gian dự án |

Tổng 9.986 token vào / 7.782 token ra, $0 (gói free). Run #2–#4 thất bại và đã dẫn tới các sửa đổi dưới đây; chúng vẫn được giữ trong Lịch sử thực thi.

### Sửa sau khi chạy thật
| Vấn đề quan sát | Sửa | Test |
|---|---|---|
| Gemini free trả 503/429 → task hết lượt thử ngay | Backoff 5/15/30/60/90s trong `call_agent`, không tính vào lượt thử của task; sự kiện `llm.retry` | ✅ |
| `gemini-3.5-flash` free chỉ 20 request/ngày/model | Phát hiện quota ngày (`PerDay`) → dừng run với thông báo đổi model; chia agent ra nhiều model flash-lite | ✅ |
| Hủy run khi đang backoff vẫn gọi LLM | Kiểm tra hủy ở đầu mỗi lượt thử và trong backoff | ✅ |
| Backend Dev kèm file `docs/`, `tests/` → cả change set bị loại | Chỉ bỏ file ngoài vùng (`files.rejected`); path thoát workspace vẫn chặn cả change set | ✅ |
| Agent không biết vì sao bị từ chối | Lỗi lần trước được đưa vào prompt lần sau | ✅ |
| Run bị hủy khi engine đã dừng để lại task "running" | Hủy đóng luôn task dở; khởi động dọn task kẹt | ✅ |
| Tóm tắt Markdown hiện thô | `react-markdown` (không render HTML thô) | trình duyệt ✅ |

`pytest`: **50/50**.

### Nhận xét chất lượng code sinh ra (chưa sửa)
- `frontend/app.js` chèn `book.title` bằng `innerHTML` → có thể XSS nếu tên sách chứa HTML. Code Reviewer chỉ được gọi khi test lỗi nên chưa phát hiện; nên thêm bước review bắt buộc.
- Trả sách chưa được mượn vẫn báo thành công (yêu cầu gốc không nói rõ).

## AI engine: AI Manager + 6 Agents + Workflow/Execution Engine · ✅ (2026-11-03)

### Quyết định
- Nhà cung cấp LLM: **Gemini API free tier**, gọi qua endpoint tương thích OpenAI. Vẫn dùng OpenAI Agents SDK; đổi sang OpenAI chỉ cần sửa `.env` (`LLM_BASE_URL`, `LLM_API_KEY`). Đã ghi vào `rules.md`.
- Agent trả output có cấu trúc. Engine ghi file và chạy lệnh, agent không có tool. Chi tiết ở `docs/AI_AGENT_DESIGN.md`.

### Đã làm
| Hạng mục | Chi tiết |
|---|---|
| Phụ thuộc | `openai-agents==0.22.3`, `openai==3.42.1`; nâng `fastapi` 0.115.6 → 0.160.0 vì openai-agents yêu cầu starlette 1.x (`pip check` sạch) |
| AI core | provider, outputs, prompts, runner, `validate_plan`, `WorkflowEngine`, Execution Engine (allowlist `pytest`), registry chạy nền + đánh dấu run dở dang khi khởi động lại |
| API | `POST /projects/{id}/runs`, `POST /runs/{id}/cancel`, `GET /llm/models`; settings có `llm_configured`, `llm_endpoint`, `require_command_approval` |
| UI | Hộp gửi yêu cầu trong Không gian dự án (ngân sách, hủy run, kết quả tổng hợp), Cài đặt: trạng thái LLM, danh sách model khả dụng, công tắc bắt buộc phê duyệt |

### Kiểm thử
| Kiểm tra | Kết quả |
|---|---|
| `pytest` toàn bộ (SQL Server `DevTeamAI_Test`) | ✅ 44/44 (10 test engine mới với `FakeModel`; pytest thật chạy trên code sinh ra) |
| `tsc -b`, `npm run lint` | ✅ 0 lỗi |
| Trình duyệt: Không gian dự án khi chưa có key | ✅ hiện "Chưa cấu hình LLM_API_KEY", nút bị khóa |
| Chạy với Gemini thật | ⏳ chờ người dùng thêm `LLM_API_KEY` |

### Phát hiện kỹ thuật
- Kiểu JSON của SQLAlchemy lưu `None` thành chuỗi `'null'`, bị `ISJSON()` từ chối → `JsonText(none_as_null=True)`.
- `openai-agents` 0.22 kéo `starlette` 1.x, không tương thích FastAPI 0.115 → nâng FastAPI.

### Còn lại
- Sau khi có key: đổi model của 7 agent sang model Gemini khả dụng (xem `GET /llm/models`), chạy thử end-to-end, tinh chỉnh prompt.
- Sandbox cho code sinh ra.

## Giao diện theo thiết kế Stitch + API đọc dữ liệu · ✅ (2026-11-03)

### Đã làm

| Hạng mục | Chi tiết |
|---|---|
| Thiết kế | Áp dụng `stitch_devteam_ai_workspace/` (13 màn hình + `DESIGN.md`): theme tối, Inter + JetBrains Mono (tự host qua fontsource), token màu surface/brand/telemetry/agent, badge trạng thái tiếng Việt |
| Layout | Sidebar 260px có badge số liệu thật (agent bật, task đang chạy, phê duyệt chờ, “Live” khi có run), top bar với bộ chọn dự án hiện tại, tìm kiếm nhật ký, bộ đếm token/chi phí; menu trượt trên mobile |
| 10 trang | Tổng quan · Dự án (thẻ + bảng) · Không gian dự án (tiến độ, timeline task, duyệt file workspace, live log) · AI Agents (Manager + 6 agent, sửa cấu hình) · Quy trình phối hợp (DAG theo phụ thuộc, chi tiết node) · Tác vụ (Kanban + danh sách) · Phê duyệt (duyệt/từ chối + audit log) · Lịch sử thực thi (lọc, tìm kiếm, phân trang, trace viewer) · Phân tích chi phí (biểu đồ ngày, theo agent/model/dự án, ngân sách) · Cài đặt (model theo agent, giới hạn, bảng giá) |
| Backend | `GET /dashboard`, `/usage/summary`, `/agents/stats`, `/runs`, `/runs/{id}`, `/runs/{id}/artifacts`, `/tasks`, `/events`, `/approvals` + approve/reject, `/settings` + PUT limits/pricing, `PATCH /agents/{id}`, `/projects/{id}/files` + content |
| Nguyên tắc dữ liệu | Không dùng số liệu mẫu của Stitch. Phần chưa có dữ liệu hiện trạng thái trống; nút “Bắt đầu phát triển bằng AI” bị khóa kèm ghi chú vì AI engine chưa có. Chi phí chỉ tính theo bảng giá người dùng nhập |

### Kiểm thử đã chạy

| Kiểm tra | Kết quả |
|---|---|
| `pytest` (SQL Server `DevTeamAI_Test`) | ✅ 34/34 (thêm 8 test API đọc, phê duyệt, settings, agent, file workspace, tìm kiếm có ký tự `[ % _`) |
| `npm run build`, `npm run lint` | ✅ (0 lỗi; 5 cảnh báo fast-refresh) |
| Trình duyệt 1440px: 10 trang với một run kiểm thử gắn nhãn chèn tạm vào DB (6 task, DAG 5 tầng, usage, event, 1 phê duyệt) | ✅ Hiển thị đúng; bấm “Từ chối” → audit log + badge sidebar cập nhật realtime. Run kiểm thử đã xóa, cascade dọn sạch toàn bộ bảng con |
| Trình duyệt 375px: 10 trang không tràn ngang | ✅ |

### Phát hiện kỹ thuật

- SQL Server: cột `BIT` không dùng trực tiếp làm điều kiện trong `CASE WHEN` → so sánh `= 1`.
- SQL Server `LIKE` coi `[` là tập ký tự; `autoescape` của SQLAlchemy không xử lý → thay `[` bằng `[[]` khi tìm kiếm nhật ký.
- Grid item mặc định `min-width: auto` khiến bảng rộng kéo giãn trang trên điện thoại → đặt `min-width: 0` cho con của `.grid`.

### Tiếp theo

- AI Manager + Workflow Engine + OpenAI Agents SDK (cần `OPENAI_API_KEY` trong `backend/.env`), `POST /projects/{id}/runs`, ghi `llm_usage` theo bảng giá.
- Execution Engine (allowlist) và tạo yêu cầu phê duyệt tự động.

## Tuần 1 – Nền tảng · ✅ Hoàn thành (2026-11-03)

### Đã làm

| Hạng mục | Chi tiết |
|---|---|
| Repo | `git init` (branch `main`), `.gitignore` (loại `.env`, `.venv`, `node_modules`, `workspaces/*`), `rules.md`, README, 9 tài liệu |
| Database | `DevTeamAI` + `DevTeamAI_Test` trên instance `localhost\BANG` (SQL Server 2022 Developer, Windows Authentication, ODBC Driver 17) |
| Migration | `1f87fbd3a806` initial schema (12 bảng), `a060f447a1ae` seed 7 agent + 19 quyền + `limits` |
| Backend | FastAPI: config `.env`, logging, lỗi chuẩn hóa, `GET /health`, Projects (list/create/get/patch), `GET /agents`, WebSocket `/ws` với hub pub/sub thread-safe |
| AI Core | `WorkspaceManager`: tạo thư mục mỗi dự án, chặn path traversal / đường dẫn tuyệt đối / UNC |
| Frontend | Vite 6 + React 19 + TS + Tailwind v4 + shadcn/ui; layout có sidebar (desktop) và thanh menu (mobile), chỉ báo kết nối SQL Server, trang Dự án (tạo, lọc, lưu trữ/khôi phục, cập nhật realtime), chi tiết dự án, trang AI Agents |
| Dev tooling | `.claude/launch.json` (backend :8000, frontend :5173), proxy Vite `/api` và `/ws` |

### Kiểm thử đã chạy

| Kiểm tra | Kết quả |
|---|---|
| `alembic upgrade head → downgrade → upgrade` (cả 2 migration) | ✅ |
| `pytest` – 26 test trên SQL Server thật (`DevTeamAI_Test`): API projects/agents/health, tiếng Việt NVARCHAR, 409/404/422, WebSocket (event, ping, topic sai), workspace guard, cascade, CHECK ISJSON | ✅ 26/26 |
| `npm run build` (tsc + vite) | ✅ |
| `npm run lint` | ✅ 0 lỗi (2 cảnh báo trong file shadcn tự sinh) |
| Trình duyệt: tạo dự án "Quản lý thư viện" qua UI → có bản ghi trong `DevTeamAI.projects` và thư mục `workspaces/quan-ly-thu-vien-…` | ✅ |
| Trình duyệt: tạo dự án bằng `curl` → bảng trên UI tự cập nhật qua WebSocket không cần reload | ✅ |
| Trang AI Agents hiển thị 7 agent, model, quyền từ DB | ✅ |

> DB `DevTeamAI` hiện có 2 dự án tạo trong lúc kiểm thử ("Quản lý thư viện", "Đặt lịch khám bệnh"). Có thể lưu trữ hoặc giữ làm dữ liệu demo.

### Phát hiện kỹ thuật

- `ISJSON()` của SQL Server trả 0 với giá trị JSON đơn (số, chuỗi) → mọi cột JSON phải chứa object/array. Đã ghi vào `rules.md`/`DATABASE_SCHEMA.md`.
- SQL Server cấm nhiều đường `ON DELETE CASCADE` → chỉ cascade theo trục `projects → workflow_runs → con`; FK phụ là NO ACTION. Đã kiểm chứng xóa project xóa sạch dữ liệu run.
- Instance `MSSQLSERVER` mặc định tắt TCP và chỉ cho Windows auth → dự án dùng instance `BANG`.

### Chưa làm / để tuần sau

- OpenAI Agents SDK, Workflow Engine, các Agent (tuần 2).
- Execution Engine, Approval Center (tuần 3).
- Dashboard, Settings, sửa cấu hình Agent, Usage charts (tuần 4).
- ODBC Driver 18 chưa cài (đang dùng 17, đổi bằng `DB_DRIVER` trong `.env`).
- Model mặc định (`gpt-5`, `gpt-5-mini`) cần xác nhận khả dụng với API key ở tuần 2.

### Việc người dùng cần chuẩn bị cho tuần 2

1. `OPENAI_API_KEY` (đặt vào `backend/.env`) và giới hạn chi tiêu trên OpenAI dashboard.
2. Xác nhận model muốn dùng cho từng Agent.
