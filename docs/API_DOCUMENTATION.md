# API Documentation

Base URL: `http://localhost:8000/api/v1` (từ frontend: `/api/v1` qua proxy Vite).
OpenAPI/Swagger tự sinh: `http://localhost:8000/docs`.

## Định dạng lỗi

| Trường hợp | HTTP | Body |
|---|---|---|
| Lỗi nghiệp vụ | 404 / 409 / 403 | `{"error": {"code": "not_found" \| "conflict" \| "workspace_access_denied", "message": "..."}}` |
| Lỗi validate | 422 | `{"detail": [{"loc": [...], "msg": "..."}]}` (chuẩn FastAPI) |

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

## Sắp có

| Tuần | Endpoint |
|---|---|
| 2 | `POST /projects/{id}/runs`, `GET /runs/{id}`, `GET /runs/{id}/tasks`, `GET /runs/{id}/artifacts`, `GET /runs/{id}/events`, `GET /usage/summary` |
| 3 | `GET /approvals`, `POST /approvals/{id}/approve`, `POST /approvals/{id}/reject`, `GET /projects/{id}/files` |
| 4 | `PATCH /agents/{id}`, `GET/PUT /settings`, `GET /dashboard` |
