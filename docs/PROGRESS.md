# Tiến độ dự án

> Từ 2026-11-03 dự án không chia theo tuần nữa; tiến độ ghi theo từng mốc chức năng.

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
