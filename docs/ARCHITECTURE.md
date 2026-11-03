# Kiến trúc DevTeam AI

## 1. Tổng thể

```
Frontend (React/Vite)  ──REST /api/v1──►  Backend FastAPI  ──pyodbc──►  SQL Server 2022
        ▲                                   │   │
        └──────── WebSocket /ws ◄───────────┘   └──OpenAI Agents SDK──► OpenAI API
                                            │
                                            └──► workspaces/<project>/ (file do Agent tạo)
```

- **Frontend** chỉ biết URL backend (qua proxy Vite). Không chứa API key/chuỗi kết nối.
- **Backend** là nơi duy nhất truy cập DB, OpenAI và filesystem.
- **AI Core** nằm trong backend (`app/ai_core`) nhưng tách module, không phụ thuộc router.

## 2. Backend – phân lớp

| Lớp | Thư mục | Trách nhiệm |
|---|---|---|
| API | `app/api/v1` | Router, validate input (Pydantic), không truy vấn DB trực tiếp |
| Service | `app/services` | Nghiệp vụ, transaction, phát sự kiện realtime |
| Repository | `app/repositories` | Truy vấn SQLAlchemy |
| Model | `app/models` | Bảng SQL Server |
| Schema | `app/schemas` | DTO request/response |
| Realtime | `app/realtime` | `RealtimeHub` pub/sub + endpoint `/ws` |
| AI Core | `app/ai_core` | Workspace (đã có), orchestrator/agents/execution (tuần 2–3) |
| Core | `app/core` | Settings từ `.env`, logging, lỗi chuẩn hóa |

Lỗi nghiệp vụ dùng `AppError` → JSON `{"error": {"code", "message"}}`.

## 3. Truy cập database

- SQLAlchemy 2 **đồng bộ** + pyodbc. Endpoint `def` chạy trong threadpool của FastAPI. Không dùng `aioodbc` (chưa ổn định với SQL Server).
- Chuỗi kết nối build từ `.env` (`Settings.database_url`), hỗ trợ Windows Authentication hoặc SQL login.
- Alembic có naming convention cố định; migration đã kiểm thử `upgrade`/`downgrade`.
- Test chạy trên DB riêng `DevTeamAI_Test` (không dùng SQLite).

## 4. Realtime

- Client mở `ws://<host>/ws?topics=projects,runs:42`.
- Topic hợp lệ: `projects`, `agents`, `approvals`, `settings`, `events`, `runs:<id>` (regex whitelist).
- Frontend: hook `useApi(fetcher, deps, topics)` tải dữ liệu và tự tải lại khi có sự kiện trên topic; `ShellProvider` giữ dữ liệu dùng chung cho sidebar/top bar (dự án hiện tại lưu ở localStorage).
- Message: `{"topic", "type", "data", "timestamp"}`. Client gửi `ping` → `{"type":"pong"}`.
- Code đồng bộ (service, worker thread) phát sự kiện bằng `hub.publish_threadsafe(...)`, an toàn giữa các thread.
- Hub chạy trong một process (MVP). Nếu chạy nhiều worker uvicorn sẽ cần broker ngoài – ngoài phạm vi MVP.

## 5. AI Core (thiết kế, triển khai tuần 2–3)

Xem chi tiết tại [AI_AGENT_DESIGN.md](AI_AGENT_DESIGN.md). Tóm tắt:

- **Manager lập kế hoạch bằng LLM** (structured output) → danh sách task + phụ thuộc.
- **Workflow Engine viết bằng code** thực thi DAG: chọn task sẵn sàng, gọi Agent, lưu artifact/usage/event, retry có giới hạn, kiểm tra ngân sách, dừng khi cần phê duyệt.
- Background runner là `asyncio` task trong process FastAPI; trạng thái lưu DB để khôi phục sau khi restart.

## 6. Bảo mật

| Cơ chế | Trạng thái |
|---|---|
| Bí mật trong `backend/.env`, không commit | ✅ |
| Frontend không chứa thông tin backend/DB | ✅ (proxy Vite) |
| Workspace Guard: chặn path traversal, đường dẫn tuyệt đối, UNC | ✅ (`ai_core/workspace/manager.py`, có test) |
| Quyền theo Agent (`agent_permissions`) | ✅ dữ liệu; áp dụng khi cấp tool ở tuần 2 |
| Execution Engine allowlist, `shell=False`, timeout | Tuần 3 |
| Approval cho thao tác nguy hiểm | Tuần 3 |
| Giới hạn retry/vòng sửa lỗi/ngân sách (`app_settings.limits`) | Dữ liệu ✅, áp dụng tuần 2–3 |
| WebSocket whitelist topic | ✅ |
