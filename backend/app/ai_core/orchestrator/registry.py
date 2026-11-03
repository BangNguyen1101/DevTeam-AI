"""Background execution of runs inside the FastAPI process (MVP: single process)."""

import asyncio
import logging

from sqlalchemy import select

from app.ai_core.llm.provider import default_model_factory
from app.ai_core.orchestrator.engine import WorkflowEngine
from app.ai_core.workspace.manager import WorkspaceManager
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Approval, ExecutionEvent, Task, WorkflowRun
from app.models.enums import ApprovalStatus, RunStatus, TaskStatus
from app.services.run import close_pending_approvals

logger = logging.getLogger(__name__)

ACTIVE = (RunStatus.PENDING, RunStatus.PLANNING, RunStatus.RUNNING, RunStatus.WAITING_APPROVAL)

_tasks: set[asyncio.Task] = set()

# Tests turn this off: startup recovery always targets the main database
RECOVER_ON_STARTUP = True


def default_engine() -> WorkflowEngine:
    return WorkflowEngine(SessionLocal, WorkspaceManager(get_settings().workspaces_path), default_model_factory)


def start_run(run_id: int, engine: WorkflowEngine | None = None) -> None:
    """Schedule a run on the running event loop; keeps a reference so it is not GC'd."""
    task = asyncio.get_running_loop().create_task((engine or default_engine()).run(run_id), name=f"run-{run_id}")
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def mark_interrupted_runs() -> int:
    """On startup, runs left active by a previous process can't resume: record that honestly."""
    if not RECOVER_ON_STARTUP:
        return 0
    with SessionLocal() as db:
        runs = list(db.scalars(select(WorkflowRun).where(WorkflowRun.status.in_(ACTIVE))))
        for run in runs:
            run.status = RunStatus.FAILED
            run.error = "Backend đã khởi động lại khi run đang chạy"
            for task in db.scalars(select(Task).where(
                Task.run_id == run.id,
                Task.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL]),
            )):
                task.status = TaskStatus.SKIPPED
            db.add(ExecutionEvent(run_id=run.id, event_type="run.failed", message=run.error))
        # Tasks left unfinished under runs that already ended (e.g. cancelled while the engine was down)
        for task in db.scalars(
            select(Task).join(WorkflowRun, WorkflowRun.id == Task.run_id).where(
                WorkflowRun.status.not_in(ACTIVE),
                Task.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL]),
            )
        ):
            task.status = TaskStatus.SKIPPED
        for run_id in db.scalars(
            select(Approval.run_id).join(WorkflowRun, WorkflowRun.id == Approval.run_id)
            .where(WorkflowRun.status.not_in(ACTIVE), Approval.status == ApprovalStatus.PENDING).distinct()
        ).all():
            close_pending_approvals(db, run_id, "Run đã kết thúc")
        db.commit()
    if runs:
        logger.warning("Marked %d interrupted run(s) as failed", len(runs))
    return len(runs)
