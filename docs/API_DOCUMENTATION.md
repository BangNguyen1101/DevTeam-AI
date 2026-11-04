# API Documentation

Base URL: `http://localhost:8000/api/v1` (từ frontend: `/api/v1` qua proxy Vite).
OpenAPI/Swagger tự sinh: `http://localhost:8000/docs`.

## Định dạng lỗi

| Trường hợp | HTTP | Body |
|---|---|---|
| Lỗi nghiệp vụ | 404 / 409 / 403 | `{"error": {"code": "not_found" \| "conflict" \| "workspace_access_denied", "message": "..."}}` |
| Lỗi validate | 422 | `{"detail": [{"loc": [...], "msg": "..."}]}` (chuẩn FastAPI) |

## Xác thực

Mọi endpoint dưới đây (trừ `/health`, `/auth/login`) và WebSocket `/ws` yêu cầu cookie phiên `devteam_session`; thiếu/hết hạn → 401 `{"error":{"code":"unauthorized"}}`.

| Endpoint | Mô tả |
|---|---|
| `POST /auth/login` | `{username, password}` → 200 `{username}` + `Set-Cookie: devteam_session` (httpOnly, SameSite=Strict, Secure nếu `COOKIE_SECURE=true`). Sai → 401 (cùng thông báo cho sai tài khoản/mật khẩu). 5 lần sai / 5 phút theo tài khoản hoặc IP → 429 `too_many_attempts` |
| `POST /auth/logout` | 204, xóa phiên phía server |
| `GET /auth/me` | `{username}` |
| `POST /auth/password` | `{current_password, new_password}` (≥ 10 ký tự) → 204, đăng xuất mọi phiên |

`ApprovalRead` có thêm `decided_by` (tên người duyệt).

## System

### `GET /health`
200 `{"status":"ok","database":{"ok":true,"server_version":"16.0.1000.6","migration":"a060f447a1ae"}}` · 503 khi không kết nối được DB.

## Projects

### `GET /projects?status=active|archived`
Danh sách dự án, mới nhất trước. Bỏ `status` để lấy tất cả.

### `POST /projects`
```json
{ "name": "Quản lý thư viện", "description": "Hệ thống mượn sách" }
```
- `name`: 1–200 ký tự, tự trim, không được rỗng, duy nhất (409 nếu trùng).
- Tạo thư mục `workspaces/<workspace_dir>`.
- 201 → `Project`. Phát sự kiện realtime `project.created`.

### `GET /projects/{id}`
200 `Project` · 404.

### `PATCH /projects/{id}`
Body (tất cả tùy chọn): `name`, `description`, `status` (`active`|`archived`). 200 `Project` · 404 · 409. Phát `project.updated`.

> Chưa có `DELETE`: dự án được lưu trữ (archive) thay vì xóa để không mất lịch sử và file workspace.

**Project**
```json
{
  "id": 1, "name": "Quản lý thư viện", "description": "…", "status": "active",
  "workspace_dir": "quan-ly-thu-vien-c36e88c9",
  "created_at": "2026-11-03T09:57:12.123", "updated_at": "…"
}
```
Thời gian là UTC (không có hậu tố `Z`).

## Agents

### `GET /agents`
Danh sách 7 agent theo thứ tự id, kèm `permissions: string[]`.

## WebSocket

`GET ws://localhost:8000/ws?topics=projects[,runs:<id>,approvals]`

| Hướng | Message |
|---|---|
| server → client (khi kết nối) | `{"type":"subscribed","topics":["projects"]}` |
| client → server | `ping` → `{"type":"pong"}` |
| server → client | `{"topic":"projects","type":"project.created"\|"project.updated","data":Project,"timestamp":"…"}` |

Topic không hợp lệ → đóng kết nối với code `1008`.

### `PATCH /agents/{id}`
Body (tùy chọn): `model` (1–100 ký tự), `max_output_tokens` (256–128000), `is_enabled`, `instructions`. 200 `Agent` · 404 · 422. Phát `agent.updated` trên topic `agents`.

### `GET /agents/stats`
Mỗi agent: `tasks_total`, `tasks_completed`, `tasks_failed`, `current_task_title`/`current_task_status` (task running/chờ duyệt mới nhất), `total_tokens`, `cost_usd`, `last_active_at`.

## Workspace files (chỉ đọc)

| Endpoint | Mô tả |
|---|---|
| `GET /projects/{id}/files` | Cây file của workspace (tối đa 2000 mục; bỏ qua `.git`, `node_modules`, `.venv`…; không theo symlink) |
| `GET /projects/{id}/files/content?path=` | Nội dung text (tối đa 200 KB, `truncated` nếu dài hơn). 403 nếu path thoát workspace · 404 · 415 với file nhị phân |

## Workflow (đọc dữ liệu do engine ghi)

| Endpoint | Mô tả |
|---|---|
| `GET /runs?project_id&status&limit` | Danh sách run kèm `tasks_total`, `tasks_completed` |
| `GET /runs/{id}` | Run + `tasks[]` (có `depends_on` theo `task_key`, token/chi phí cộng từ `llm_usage`) |
| `GET /runs/{id}/artifacts` | Sản phẩm của các agent |
| `GET /tasks?project_id&run_id&agent_code&status` | Tác vụ (tối đa 500) |
| `GET /events?project_id&run_id&agent_code&event_type&q&before_id&limit` | Nhật ký thực thi, mới nhất trước, phân trang bằng `before_id` → `{items, total, next_before_id}`. `q` tìm theo nội dung, ký tự `% _ [` được hiểu theo nghĩa đen |
| `GET /approvals?status` | Yêu cầu phê duyệt |
| `POST /approvals/{id}/approve` · `/reject` | Body `{note?}`. 409 nếu đã quyết định. Ghi `execution_events` (`approval.approved/rejected`), phát `approval.decided` trên `approvals` và `runs:{run_id}` |

## Analytics & Settings

| Endpoint | Mô tả |
|---|---|
| `GET /dashboard` | Số liệu tổng: dự án, run đang chạy, task theo trạng thái, tỉ lệ thành công, agent bật, token/chi phí, phê duyệt chờ, tiến độ run mới nhất của từng dự án |
| `GET /usage/summary?days=1..365&project_id` | `totals`, `by_agent`, `by_day`, `by_model`, `by_project`, `monthly_budget_usd`, `month_cost_usd` |
| `GET /settings` | `limits`, `pricing` (USD/1M token theo model), `openai_key_configured` (chỉ true/false, không trả key) |
| `PUT /settings/limits` | `max_task_attempts` 1–10, `max_fix_iterations` 0–10, `command_timeout_seconds` 5–1800, `default_run_budget_usd`, `monthly_budget_usd?` |
| `PUT /settings/pricing` | `{ "<model>": {input_per_1m, cached_input_per_1m, output_per_1m} }` |

Topic WebSocket hợp lệ: `projects`, `agents`, `approvals`, `settings`, `events`, `runs:<id>`.

## Xem trước ứng dụng

| Endpoint | Mô tả |
|---|---|
| `GET /projects/{id}/preview` | `{running, url, api_running, started_at, log_tail}` |
| `POST /projects/{id}/preview` | Chạy backend do AI viết (nếu có `backend/app/main.py`) và trả `url` = `/preview/{token}/`. 409 nếu thiếu `frontend/index.html`, đã đủ 2 bản chạy, hoặc backend không khởi động được (kèm log) |
| `DELETE /projects/{id}/preview` | 204, dừng tiến trình |
| `GET /preview/{token}/{path}` (công khai theo token) | File trong `frontend/`, header `Content-Security-Policy: sandbox …` |
| `* /preview/{token}/api/{path}` | Proxy tới backend của ứng dụng, có CORS `*` cho origin sandbox |

## Runs (AI engine)

| Endpoint | Mô tả |
|---|---|
| `POST /projects/{id}/runs` | Body `{request_text (10–10000 ký tự), budget_usd?}`. 201 `RunDetail` và engine chạy nền. 503 `llm_not_configured` nếu chưa có `LLM_API_KEY` · 404 · 409 nếu dự án lưu trữ hoặc đang có run chưa kết thúc |
| `POST /runs/{id}/cancel` | 204. 409 nếu run đã kết thúc |
| `GET /llm/models` | Danh sách model của nhà cung cấp LLM đang cấu hình |

`GET /settings` trả thêm `llm_configured`, `llm_endpoint` (hostname). `limits.require_command_approval` (mặc định `true`) quyết định có phải phê duyệt trước khi chạy test hay không.
