from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_core.llm.provider import LlmNotConfiguredError, llm_configured
from app.core.exceptions import ConflictError, NotFoundError
from app.models import Approval, ExecutionEvent, Project, Task, WorkflowRun
from app.models.enums import ApprovalStatus, ProjectStatus, RunStatus, TaskStatus
from app.realtime.hub import hub
from app.services.settings import SettingsService

ACTIVE = (RunStatus.PENDING, RunStatus.PLANNING, RunStatus.RUNNING, RunStatus.WAITING_APPROVAL)
UNFINISHED_TASKS = (TaskStatus.PENDING, TaskStatus.READY, TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL)


class RunService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, project_id: int, request_text: str, budget_usd: float | None) -> WorkflowRun:
        if not llm_configured():
            raise LlmNotConfiguredError("Chưa cấu hình LLM_API_KEY trong backend/.env")
        project = self.db.get(Project, project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found")
        if project.status != ProjectStatus.ACTIVE:
            raise ConflictError("Dự án đã lưu trữ, hãy khôi phục trước khi tạo run")
        # Agents write into one shared workspace, so runs of a project must not overlap
        if self.db.scalar(select(WorkflowRun.id).where(WorkflowRun.project_id == project_id, WorkflowRun.status.in_(ACTIVE))):
            raise ConflictError("Dự án đang có một run chưa kết thúc")
        budget = budget_usd if budget_usd is not None else SettingsService(self.db).limits().default_run_budget_usd
        run = WorkflowRun(project_id=project_id, request_text=request_text, budget_usd=Decimal(str(budget)))
        self.db.add(run)
        self.db.flush()
        self.db.add(ExecutionEvent(run_id=run.id, event_type="run.created", message="Người dùng gửi yêu cầu mới"))
        self.db.commit()
        hub.publish_threadsafe("events", "run.created", {"run_id": run.id, "project_id": project_id})
        return run

    def cancel(self, run_id: int) -> None:
        run = self.db.get(WorkflowRun, run_id)
        if run is None:
            raise NotFoundError(f"Run {run_id} not found")
        if run.status not in ACTIVE:
            raise ConflictError(f"Run đã kết thúc ({run.status.value})")
        # The engine notices the status between tasks / while waiting for approval;
        # unfinished tasks are closed here too so nothing stays "running" if the engine is gone
        run.status = RunStatus.CANCELLED
        run.finished_at = datetime.now(UTC).replace(tzinfo=None)
        for task in self.db.scalars(select(Task).where(Task.run_id == run_id, Task.status.in_(UNFINISHED_TASKS))):
            task.status = TaskStatus.SKIPPED
        close_pending_approvals(self.db, run_id, "Run đã bị hủy")
        self.db.add(ExecutionEvent(run_id=run.id, event_type="run.cancel_requested", message="Người dùng yêu cầu hủy run"))
        self.db.commit()
        hub.publish_threadsafe(f"runs:{run_id}", "run.cancel_requested", {"run_id": run_id})
        hub.publish_threadsafe("approvals", "approval.closed", {"run_id": run_id})


def close_pending_approvals(db: Session, run_id: int, reason: str) -> None:
    """A finished run can't act on approvals anymore; don't leave them waiting in the center."""
    now = datetime.now(UTC).replace(tzinfo=None)
    for approval in db.scalars(select(Approval).where(Approval.run_id == run_id, Approval.status == ApprovalStatus.PENDING)):
        approval.status = ApprovalStatus.REJECTED
        approval.decision_note = reason
        approval.decided_at = now
