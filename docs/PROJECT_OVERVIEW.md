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

| # | Phân hệ | Trạng thái |
|---|---|---|
| 1 | Dashboard | ✅ Giao diện + số liệu thật |
| 2 | Project Management | ✅ |
| 3 | Project Workspace | ✅ Xem tiến độ, file, log · ⏳ gửi yêu cầu cho AI Manager |
| 4 | AI Agent Management | ✅ Xem + sửa model/token/bật-tắt/chỉ dẫn |
| 5 | Workflow | ✅ Hiển thị DAG · ⏳ engine thực thi |
| 6 | Task Management | ✅ Kanban + danh sách |
| 7 | Approval Center | ✅ Duyệt/từ chối + audit log · ⏳ engine tạo yêu cầu |
| 8 | Execution History | ✅ |
| 9 | Usage & Cost Analytics | ✅ Hiển thị · ⏳ engine ghi `llm_usage` |
| 10 | Settings | ✅ Model, giới hạn, bảng giá |

Giao diện theo thiết kế Stitch trong `stitch_devteam_ai_workspace/` (xem `devteam_ai_platform_system/DESIGN.md`).

## Phạm vi MVP (4 tuần)

- Một người dùng (admin), chưa có đăng nhập.
- Phần mềm do Agent sinh ra là ứng dụng nhỏ (API CRUD + giao diện đơn giản). QA chạy `pytest` cho backend sinh ra; frontend sinh ra chỉ kiểm tra tĩnh.
- Ưu tiên một luồng end-to-end chạy thật hơn là nhiều màn hình.
