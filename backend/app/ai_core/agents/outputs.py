"""Structured outputs returned by each agent (OpenAI Agents SDK `output_type`)."""

from typing import Literal

from pydantic import BaseModel, Field

WorkerCode = Literal["business_analyst", "architect", "backend_dev", "frontend_dev", "qa_tester"]


class PlannedTask(BaseModel):
    key: str = Field(description="Mã ngắn duy nhất, chữ thường/số/gạch dưới, ví dụ 'ba', 'arch', 'be'")
    agent_code: WorkerCode
    title: str = Field(description="Tiêu đề tác vụ ngắn gọn, tiếng Việt")
    description: str = Field(description="Mô tả cụ thể việc agent cần làm cho yêu cầu này")
    depends_on: list[str] = Field(description="Các key phải hoàn thành trước")


class Plan(BaseModel):
    analysis: str = Field(description="Phân tích ngắn yêu cầu và phạm vi MVP")
    tasks: list[PlannedTask]


class Document(BaseModel):
    filename: str = Field(description="Tên file markdown, ví dụ 'SRS.md'")
    content: str = Field(description="Toàn bộ nội dung tài liệu dạng Markdown")
    summary: str = Field(description="Tóm tắt 2-3 câu cho agent tiếp theo")


class FileChange(BaseModel):
    path: str = Field(description="Đường dẫn tương đối trong workspace, dùng dấu '/'")
    content: str = Field(default="", description="Toàn bộ nội dung mới của file (bỏ trống khi delete=true)")
    delete: bool = Field(default=False, description="true để xóa file cũ không còn phù hợp")


class CodeChangeSet(BaseModel):
    summary: str = Field(description="Những gì đã làm và cách chạy/kiểm tra")
    files: list[FileChange]


class ReviewResult(BaseModel):
    root_cause: str = Field(description="Nguyên nhân gốc của lỗi kiểm thử")
    issues: list[str] = Field(description="Các vấn đề chất lượng/bảo mật phát hiện được")
    files: list[FileChange] = Field(description="Các file đã sửa (nội dung đầy đủ)")
    summary: str


class RunSummary(BaseModel):
    summary: str = Field(description="Tổng hợp kết quả cho người dùng, tiếng Việt, dạng Markdown ngắn")
