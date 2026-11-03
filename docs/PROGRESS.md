# Tiến độ dự án

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
