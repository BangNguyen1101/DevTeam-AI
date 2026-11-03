from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApprovalStatus, RunStatus, TaskStatus


class TaskRead(BaseModel):
    id: int
    run_id: int
    project_id: int
    project_name: str
    agent_code: str
    agent_name: str
    task_key: str
    title: str
    description: str | None
    status: TaskStatus
    attempt: int
    max_attempts: int
    error: str | None
    depends_on: list[str]
    input_tokens: int
    output_tokens: int
    cost_usd: float
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RunRead(BaseModel):
    id: int
    project_id: int
    project_name: str
    request_text: str
    status: RunStatus
    budget_usd: float | None
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    summary: str | None
    error: str | None
    tasks_total: int
    tasks_completed: int
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class RunDetail(RunRead):
    tasks: list[TaskRead]


class ArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    task_id: int | None
    kind: str
    name: str
    file_path: str | None
    created_at: datetime


class EventRead(BaseModel):
    id: int
    run_id: int
    project_id: int
    project_name: str
    task_id: int | None
    task_title: str | None
    agent_code: str | None
    event_type: str
    message: str
    data: dict[str, Any] | list[Any] | None
    created_at: datetime


class EventPage(BaseModel):
    items: list[EventRead]
    total: int
    next_before_id: int | None


class ApprovalRead(BaseModel):
    id: int
    run_id: int
    project_id: int
    project_name: str
    task_id: int | None
    agent_code: str | None
    kind: str
    title: str
    payload: dict[str, Any] | list[Any] | None
    status: ApprovalStatus
    decision_note: str | None
    decided_at: datetime | None
    created_at: datetime


class RunCreate(BaseModel):
    request_text: str = Field(min_length=10, max_length=10_000)
    budget_usd: float | None = Field(default=None, ge=0, le=1000)


class ApprovalDecision(BaseModel):
    note: str | None = Field(default=None, max_length=2000)
