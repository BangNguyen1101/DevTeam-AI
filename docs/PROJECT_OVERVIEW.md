# Tổng quan dự án DevTeam AI

## Mục tiêu

Xây dựng một "đội phát triển phần mềm AI": người dùng mô tả yêu cầu, **AI Manager** phân rã thành nhiệm vụ và điều phối **6 Agent chuyên môn** phối hợp thật sự (kết quả Agent trước là đầu vào Agent sau) để tạo ra tài liệu, code và kết quả kiểm thử trong workspace riêng của dự án.

## Thành phần

| Thành phần | Mã (`agents.code`) | Vai trò chính |
|---|---|---|
| AI Manager | `manager` | Phân tích yêu cầu, lập kế hoạch (DAG nhiệm vụ), phân công, tổng hợp |
| Business Analyst | `business_analyst` | User stories, acceptance criteria, SRS |
| Software Architect | `architect` | Kiến trúc, database, API, tài liệu kỹ thuật |
| Backend Developer | `backend_dev` | API, nghiệp vụ, database |
| Frontend Developer | `frontend_dev` | Giao diện, kết nối API |
| QA Tester | `qa_tester` | Test case, chạy test, báo lỗi, test lại |
| Code Reviewer & Debugger | `code_reviewer` | Review chất lượng/bảo mật, phân tích và sửa lỗi |

## Quy trình

```
User → AI Manager (lập kế hoạch)
     → BA → Architect → [Backend ∥ Frontend] → QA
     → (lỗi) Reviewer sửa → QA test lại (tối đa N vòng)
     → AI Manager tổng hợp kết quả
```

## Phân hệ

| # | Phân hệ | Tuần hoạt động |
|---|---|---|
| 1 | Dashboard | 4 |
| 2 | Project Management | **1 (đã có)** |
| 3 | Project Workspace | 1 (tạo thư mục), 3 (duyệt file) |
| 4 | AI Agent Management | **1 (xem)**, 4 (sửa cấu hình) |
| 5 | Workflow | 2 |
| 6 | Task Management | 2 |
| 7 | Approval Center | 3 |
| 8 | Execution History | 2–4 |
| 9 | Usage & Cost Analytics | 2 (ghi nhận), 4 (biểu đồ) |
| 10 | Settings | 4 |

## Phạm vi MVP (4 tuần)

- Một người dùng (admin), chưa có đăng nhập.
- Phần mềm do Agent sinh ra là ứng dụng nhỏ (API CRUD + giao diện đơn giản). QA chạy `pytest` cho backend sinh ra; frontend sinh ra chỉ kiểm tra tĩnh.
- Ưu tiên một luồng end-to-end chạy thật hơn là nhiều màn hình.
