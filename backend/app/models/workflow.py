"""Workflow runs and everything produced while a run executes.

SQL Server rejects multiple cascade paths, so only the run -> child FKs cascade;
secondary FKs (task_id, agent_id, approval_id) use NO ACTION.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, Numeric, Unicode, UnicodeText, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, DateTime2, JsonText, TimestampMixin
from app.models.enums import ApprovalStatus, CommandStatus, RunStatus, TaskStatus, str_enum


def _json_check(column: str) -> CheckConstraint:
    return CheckConstraint(f"{column} IS NULL OR ISJSON({column}) = 1", name=f"{column}_json")


class WorkflowRun(TimestampMixin, Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    request_text: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        str_enum(RunStatus, "run_status"), server_default=RunStatus.PENDING.value, nullable=False
    )
    budget_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    total_input_tokens: Mapped[int] = mapped_column(BigInteger, server_default="0", nullable=False)
    total_output_tokens: Mapped[int] = mapped_column(BigInteger, server_default="0", nullable=False)
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), server_default="0", nullable=False)
    summary: Mapped[str | None] = mapped_column(UnicodeText)
    error: Mapped[str | None] = mapped_column(UnicodeText)
    started_at: Mapped[datetime | None] = mapped_column(DateTime2())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime2())

    project: Mapped["Project"] = relationship(back_populates="runs")  # noqa: F821
    tasks: Mapped[list["Task"]] = relationship(back_populates="run", passive_deletes=True)


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("run_id", "task_key"),
        _json_check("input_data"),
        _json_check("output_data"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True, nullable=False)
    # Stable identifier inside a run, used by the planner to express dependencies
    task_key: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    title: Mapped[str] = mapped_column(Unicode(300), nullable=False)
    description: Mapped[str | None] = mapped_column(UnicodeText)
    status: Mapped[TaskStatus] = mapped_column(
        str_enum(TaskStatus, "task_status"), server_default=TaskStatus.PENDING.value, nullable=False
    )
    attempt: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, server_default="3", nullable=False)
    input_data: Mapped[dict[str, Any] | None] = mapped_column(JsonText)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JsonText)
    error: Mapped[str | None] = mapped_column(UnicodeText)
    started_at: Mapped[datetime | None] = mapped_column(DateTime2())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime2())

    run: Mapped[WorkflowRun] = relationship(back_populates="tasks")


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (CheckConstraint("task_id <> depends_on_task_id", name="no_self_dependency"),)

    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
    depends_on_task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), primary_key=True)


class Artifact(Base):
    """Work product of an agent (requirements spec, design doc, source file, test report...)."""

    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), index=True)
    kind: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    name: Mapped[str] = mapped_column(Unicode(300), nullable=False)
    content: Mapped[str | None] = mapped_column(UnicodeText)
    # Path relative to the project workspace when the artifact is a file
    file_path: Mapped[str | None] = mapped_column(Unicode(500))
    created_at: Mapped[datetime] = mapped_column(DateTime2(), server_default=func.sysutcdatetime(), nullable=False)


class Approval(Base):
    __tablename__ = "approvals"
    __table_args__ = (_json_check("payload"), Index(None, "status", "created_at"))

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"))
    kind: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    title: Mapped[str] = mapped_column(Unicode(300), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JsonText)
    status: Mapped[ApprovalStatus] = mapped_column(
        str_enum(ApprovalStatus, "approval_status"), server_default=ApprovalStatus.PENDING.value, nullable=False
    )
    decision_note: Mapped[str | None] = mapped_column(UnicodeText)
    decided_by: Mapped[str | None] = mapped_column(Unicode(100))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime2())
    created_at: Mapped[datetime] = mapped_column(DateTime2(), server_default=func.sysutcdatetime(), nullable=False)


class ExecutionEvent(Base):
    """Append-only timeline of a run; also the source of WebSocket messages."""

    __tablename__ = "execution_events"
    __table_args__ = (_json_check("data"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"))
    event_type: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    message: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    data: Mapped[dict[str, Any] | None] = mapped_column(JsonText)
    created_at: Mapped[datetime] = mapped_column(DateTime2(), server_default=func.sysutcdatetime(), nullable=False)


class CommandExecution(Base):
    __tablename__ = "command_executions"
    __table_args__ = (_json_check("args"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"))
    approval_id: Mapped[int | None] = mapped_column(ForeignKey("approvals.id"))
    command: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    args: Mapped[list[str] | None] = mapped_column(JsonText)
    cwd: Mapped[str] = mapped_column(Unicode(500), nullable=False)
    status: Mapped[CommandStatus] = mapped_column(
        str_enum(CommandStatus, "command_status"), server_default=CommandStatus.PENDING.value, nullable=False
    )
    exit_code: Mapped[int | None] = mapped_column(Integer)
    stdout: Mapped[str | None] = mapped_column(UnicodeText)
    stderr: Mapped[str | None] = mapped_column(UnicodeText)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime2(), server_default=func.sysutcdatetime(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime2())


class LlmUsage(Base):
    """One row per model call; the basis of Usage & Cost Analytics."""

    __tablename__ = "llm_usage"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"))
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True, nullable=False)
    model: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cached_input_tokens: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime2(), server_default=func.sysutcdatetime(), nullable=False)
