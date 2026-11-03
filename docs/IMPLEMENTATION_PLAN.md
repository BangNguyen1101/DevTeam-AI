# Kế hoạch triển khai (4 tuần)

> **Cập nhật 2026-11-03:** dự án không còn chia theo tuần; làm liên tục theo mốc chức năng. Toàn bộ giao diện 10 phân hệ và các API đọc đã xong trước (xem PROGRESS.md). Thứ tự còn lại: AI Manager + Workflow Engine + BA/Architect → Backend/Frontend Dev + Execution Engine + QA/Reviewer + phê duyệt tự động → hoàn thiện demo. Các bảng bên dưới giữ lại làm tham chiếu phạm vi.

Mục tiêu MVP: trình diễn được một Run thật từ yêu cầu → AI Manager → BA → Architect → Backend ∥ Frontend → QA → Reviewer → QA → tổng hợp, với dữ liệu thật trong SQL Server và cập nhật realtime.

## Tuần 1 – Nền tảng ✅

| Hạng mục | Kiểm chứng |
|---|---|
| Git, `.gitignore`, `rules.md`, README, docs | File tồn tại, thống nhất với code |
| Backend skeleton: config `.env`, logging, lỗi chuẩn hóa | `GET /health` |
| SQL Server + SQLAlchemy + Alembic, schema 12 bảng, seed agent | `alembic upgrade/downgrade`, xem bảng trong SSMS |
| Projects CRUD + tạo workspace | pytest + tạo dự án qua UI |
| WebSocket hub | pytest + UI tự cập nhật khi client khác tạo dự án |
| Frontend: layout, Projects, Project detail, Agents | `npm run build`, kiểm tra trên trình duyệt |

## Tuần 2 – AI Core (nửa đầu)

1. Thêm `openai-agents` (ghim version), cấu hình `OPENAI_API_KEY`, bảng giá model trong `app_settings`.
2. Adapter Agent: build `Agent` từ bảng `agents` + instructions + output_type.
3. Manager `plan()` + validate DAG → `tasks`, `task_dependencies`.
4. Workflow Engine: vòng lặp chọn task ready, retry, budget, ghi `execution_events`, phát WebSocket `runs:<id>`, khôi phục run dở dang khi khởi động.
5. Agent BA + Architect với tool ghi tài liệu vào workspace.
6. Usage tracker → `llm_usage`.
7. API Runs/Tasks/Artifacts/Events; UI: form gửi yêu cầu, trang Workflow (timeline realtime), danh sách Task.

**Kiểm chứng:** một yêu cầu thật sinh `docs/SRS.md` và `docs/DESIGN.md` trong workspace, token/chi phí có trong `llm_usage`, UI cập nhật trực tiếp.

## Tuần 3 – Dev, QA và vòng sửa lỗi

1. Tool `read_file`/`list_dir`/`write_file` có kiểm tra quyền theo vùng.
2. Agent Backend ∥ Frontend.
3. Execution Engine (allowlist, timeout, env sạch) → `command_executions`.
4. QA sinh test + chạy `pytest`; Reviewer sửa; QA test lại (giới hạn vòng).
5. Approval Center: lệnh ngoài allowlist / vượt ngân sách → `approvals`, dừng và tiếp tục run.
6. UI: Approvals, duyệt file workspace, xem artifact.

**Kiểm chứng:** một Run hoàn chỉnh tạo code có test chạy được; lệnh ngoài allowlist bị chặn và xuất hiện trong Approval Center.

## Tuần 4 – Hoàn thiện và demo

1. Dashboard, Execution History, Usage & Cost (biểu đồ), Settings (model, giới hạn), sửa cấu hình Agent.
2. Xử lý lỗi, hủy run, test end-to-end.
3. Kịch bản demo, chạy thử 2–3 lần liên tiếp.
4. Hoàn thiện tài liệu.

## Phụ thuộc

```
T1 nền tảng ─► T2 engine + BA/Architect ─► T3 Dev/QA/Reviewer + Approval ─► T4 UI tổng hợp + demo
```
