# Quy tắc phát triển DevTeam AI

Tài liệu này là "luật" bắt buộc cho mọi người (và mọi AI) tham gia phát triển dự án.

## 1. Công nghệ (không tự ý thay đổi)

| Lớp | Công nghệ |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Backend | Python 3.11, FastAPI, Pydantic v2 |
| Database | **Microsoft SQL Server** (duy nhất), SQLAlchemy 2.x, Alembic, pyodbc, Microsoft ODBC Driver for SQL Server |
| AI | OpenAI API, OpenAI Agents SDK |
| Realtime | WebSocket |

- Không dùng SQLite/PostgreSQL/MySQL, kể cả cho test. Test chạy trên database SQL Server riêng (`DevTeamAI_Test`).
- Thay đổi công nghệ hoặc kiến trúc lớn phải trình bày phương án và chờ phê duyệt.

## 2. Bảo mật

- Mọi bí mật (API key, chuỗi kết nối DB) chỉ nằm trong `backend/.env` (không commit). `.env.example` chỉ chứa giá trị mẫu.
- Frontend **không bao giờ** chứa API key hoặc thông tin DB. Frontend chỉ biết URL của Backend.
- Agent chỉ được truy cập file trong `workspaces/<project_id>/`. Mọi đường dẫn phải qua Workspace Guard.
- Không thực thi shell tùy ý. Lệnh chỉ chạy qua Execution Engine với allowlist, `shell=False`, có timeout.
- Thao tác nguy hiểm (lệnh ngoài allowlist, xóa file, vượt ngân sách) phải tạo yêu cầu trong Approval Center.

## 3. Database (SQL Server)

- Văn bản dùng `NVARCHAR` (collation instance là Latin1, tiếng Việt cần Unicode).
- Thời gian dùng `DATETIME2`, lưu UTC.
- JSON lưu trong `NVARCHAR(MAX)` kèm `CHECK (ISJSON(col) = 1)`. Giá trị phải là object/array (`ISJSON` từ chối số/chuỗi đơn).
- Chỉ cascade theo trục `projects → workflow_runs → bảng con`; FK phụ dùng NO ACTION (SQL Server cấm nhiều đường cascade).
- Khóa chính `BIGINT IDENTITY`.
- Mọi thay đổi schema phải qua Alembic migration; review file migration trước khi chạy; migration phải `downgrade` được.
- Constraint có tên cố định nhờ naming convention trong `app/db/base.py`.

## 4. Code

- Backend phân lớp: `api` → `services` → `repositories` → `models`. Router không truy vấn DB trực tiếp.
- Schema request/response dùng Pydantic (`app/schemas`), không trả model ORM ra ngoài.
- Không viết code trùng lặp, không tạo module chưa dùng tới.
- Frontend tổ chức theo `features/<module>`; gọi API qua `src/lib/api.ts`.
- Đặt tên: Python `snake_case`, TypeScript `camelCase`/`PascalCase` cho component.

## 5. Quy trình

1. Hiểu rõ mục đích và vị trí file trước khi tạo/sửa.
2. Mỗi chức năng phải có cách kiểm tra cụ thể (test tự động hoặc bước kiểm thử thủ công ghi trong PROGRESS.md).
3. Không tuyên bố hoàn thành khi chưa kiểm thử. Không dùng dữ liệu giả để chứng minh chức năng hoạt động.
4. Sau mỗi giai đoạn cập nhật `docs/PROGRESS.md`.
5. Commit nhỏ, thông điệp rõ ràng.
