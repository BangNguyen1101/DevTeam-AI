# DevTeam AI

Nền tảng phát triển phần mềm theo kiến trúc **Multi-AI Agent**: một AI Manager điều phối 6 Agent chuyên môn (Business Analyst, Software Architect, Backend Developer, Frontend Developer, QA Tester, Code Reviewer & Debugger) để đi từ yêu cầu người dùng đến code đã được kiểm thử.

- Tổng quan: [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)
- Kiến trúc: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Tiến độ: [docs/PROGRESS.md](docs/PROGRESS.md)
- Quy tắc phát triển: [rules.md](rules.md)

## Công nghệ

React 19 + TypeScript + Vite + Tailwind CSS v4 + shadcn/ui · Python 3.11 + FastAPI + Pydantic v2 · Microsoft SQL Server 2022 + SQLAlchemy 2 + Alembic + pyodbc · OpenAI API / Agents SDK · WebSocket.

## Cấu trúc thư mục

```
DevTeam-AI/
├── backend/            FastAPI + AI Core
│   ├── app/
│   │   ├── api/v1/     REST routers
│   │   ├── services/   nghiệp vụ
│   │   ├── repositories/
│   │   ├── models/     SQLAlchemy models
│   │   ├── schemas/    Pydantic request/response
│   │   ├── realtime/   WebSocket hub
│   │   ├── ai_core/    orchestrator, agents, workspace, execution (từ tuần 2)
│   │   ├── core/       config, logging, exceptions
│   │   └── db/         engine, session, naming convention
│   ├── alembic/        migrations
│   └── tests/          pytest (chạy trên SQL Server DevTeamAI_Test)
├── frontend/           React app (src/features/<module>)
├── docs/               tài liệu kỹ thuật
├── scripts/            create_db.sql
├── workspaces/         thư mục làm việc của Agent cho từng dự án (không commit)
└── rules.md
```

## Chạy bằng Docker (khuyên dùng)

Yêu cầu: Docker Desktop đang chạy, máy còn trống khoảng 3 GB RAM.

```powershell
Copy-Item .env.example .env      # điền MSSQL_SA_PASSWORD, ADMIN_PASSWORD, LLM_API_KEY
docker compose up -d --build     # lần đầu mất vài phút (tải SQL Server, build image)
docker compose logs -f backend   # đợi dòng "Application startup complete"
```

Mở **http://localhost:8080** và đăng nhập bằng `ADMIN_USERNAME` / `ADMIN_PASSWORD`.

| Dịch vụ | Vai trò |
|---|---|
| `db` | SQL Server 2022 (Linux), dữ liệu trong volume `mssql-data`, không mở cổng ra ngoài |
| `backend` | FastAPI; lúc khởi động tự tạo database, chạy `alembic upgrade head`, tạo admin đầu tiên. Chạy bằng user không phải root; code do agent sinh ra nằm trong volume `workspaces` |
| `web` | nginx phục vụ frontend đã build và proxy `/api`, `/ws` tới backend (cùng origin); chỉ lắng nghe trên `127.0.0.1` |

Các lệnh khác: `docker compose down` (dừng, giữ dữ liệu) · `docker compose down -v` (**xóa** cả database và workspace) · `docker compose exec backend python -m app.cli set-password admin` (đặt lại mật khẩu).

## Bảo mật đăng nhập

- Mọi API (trừ `/api/v1/health`, `/api/v1/auth/login`) và WebSocket đều yêu cầu đăng nhập.
- Mật khẩu hash bằng **scrypt** (N=2^17); session lưu phía server, cookie `httpOnly` + `SameSite=Strict`; DB chỉ lưu SHA-256 của token.
- Sai mật khẩu 5 lần / 5 phút (theo tài khoản và theo IP) → khóa tạm (429). Thông báo lỗi không tiết lộ tài khoản có tồn tại hay không.
- Đổi mật khẩu trong **Cài đặt → Hệ thống** (đăng xuất mọi phiên). Người duyệt được ghi vào nhật ký phê duyệt.

## Chạy trực tiếp trên Windows (phát triển)

### Yêu cầu môi trường

- Windows 10/11, Node.js ≥ 20, Python 3.11, Git
- SQL Server 2022 (instance có TCP bật), SSMS
- Microsoft ODBC Driver 17 hoặc 18 for SQL Server (khuyến nghị 18)

## Cài đặt lần đầu

```powershell
# 1. Database (tạo DevTeamAI và DevTeamAI_Test)
sqlcmd -S localhost\BANG -E -i scripts\create_db.sql

# 2. Backend
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env          # chỉnh DB_SERVER, DB_DRIVER, đặt ADMIN_PASSWORD và LLM_API_KEY
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\alembic.exe -x db=DevTeamAI_Test upgrade head

# 3. Frontend
cd ..\frontend
npm install
```

## Chạy ứng dụng

```powershell
# Terminal 1 – backend: http://localhost:8000 (Swagger: /docs)
cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# Terminal 2 – frontend: http://localhost:5173
cd frontend; npm run dev
```

Frontend gọi backend qua proxy của Vite (`/api`, `/ws`), nên không có thông tin backend/DB nào nằm trong bundle frontend.

## Kiểm thử

```powershell
cd backend; .\.venv\Scripts\python.exe -m pytest -q     # cần SQL Server đang chạy
cd frontend; npm run build; npm run lint
```
