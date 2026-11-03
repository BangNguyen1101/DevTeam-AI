"""Read side of workflow data (runs, tasks, events, approvals) for the UI.

Writes come from the workflow engine; the only user write here is an approval decision.
"""

from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Agent, Approval, Artifact, ExecutionEvent, LlmUsage, Project, Task, TaskDependency, WorkflowRun
from app.models.enums import ApprovalStatus, RunStatus, TaskStatus
from app.realtime.hub import hub
from app.schemas.workflow import (
    ApprovalRead,
    ArtifactRead,
    EventPage,
    EventRead,
    RunDetail,
    RunRead,
    TaskRead,
)

MAX_TASKS = 500


def _task_usage_subquery():
    return (
        select(
            LlmUsage.task_id.label("task_id"),
            func.sum(LlmUsage.input_tokens).label("input_tokens"),
            func.sum(LlmUsage.output_tokens).label("output_tokens"),
            func.sum(LlmUsage.cost_usd).label("cost_usd"),
        )
        .where(LlmUsage.task_id.is_not(None))
        .group_by(LlmUsage.task_id)
        .subquery()
    )


def _run_counts_subquery():
    return (
        select(
            Task.run_id.label("run_id"),
            func.count().label("total"),
            func.sum(case((Task.status == TaskStatus.COMPLETED, 1), else_=0)).label("completed"),
        )
        .group_by(Task.run_id)
        .subquery()
    )


class WorkflowQueryService:
    def __init__(self, db: Session):
        self.db = db

    # ---- runs ---------------------------------------------------------------

    def list_runs(self, project_id: int | None = None, status: RunStatus | None = None, limit: int = 100) -> list[RunRead]:
        counts = _run_counts_subquery()
        stmt = (
            select(WorkflowRun, Project.name, counts.c.total, counts.c.completed)
            .join(Project, Project.id == WorkflowRun.project_id)
            .outerjoin(counts, counts.c.run_id == WorkflowRun.id)
            .order_by(WorkflowRun.id.desc())
            .limit(limit)
        )
        if project_id is not None:
            stmt = stmt.where(WorkflowRun.project_id == project_id)
        if status is not None:
            stmt = stmt.where(WorkflowRun.status == status)
        return [self._run(run, name, total, done) for run, name, total, done in self.db.execute(stmt)]

    def get_run(self, run_id: int) -> RunDetail:
        counts = _run_counts_subquery()
        row = self.db.execute(
            select(WorkflowRun, Project.name, counts.c.total, counts.c.completed)
            .join(Project, Project.id == WorkflowRun.project_id)
            .outerjoin(counts, counts.c.run_id == WorkflowRun.id)
            .where(WorkflowRun.id == run_id)
        ).first()
        if row is None:
            raise NotFoundError(f"Run {run_id} not found")
        run = self._run(*row)
        return RunDetail(**run.model_dump(), tasks=self.list_tasks(run_id=run_id))

    def list_artifacts(self, run_id: int) -> list[ArtifactRead]:
        stmt = select(Artifact).where(Artifact.run_id == run_id).order_by(Artifact.id)
        return [ArtifactRead.model_validate(a) for a in self.db.scalars(stmt)]

    @staticmethod
    def _run(run: WorkflowRun, project_name: str, total: int | None, completed: int | None) -> RunRead:
        return RunRead(
            id=run.id,
            project_id=run.project_id,
            project_name=project_name,
            request_text=run.request_text,
            status=run.status,
            budget_usd=float(run.budget_usd) if run.budget_usd is not None else None,
            total_input_tokens=run.total_input_tokens,
            total_output_tokens=run.total_output_tokens,
            total_cost_usd=float(run.total_cost_usd),
            summary=run.summary,
            error=run.error,
            tasks_total=total or 0,
            tasks_completed=completed or 0,
            started_at=run.started_at,
            finished_at=run.finished_at,
            created_at=run.created_at,
        )

    # ---- tasks --------------------------------------------------------------

    def list_tasks(
        self,
        project_id: int | None = None,
        run_id: int | None = None,
        agent_code: str | None = None,
        status: TaskStatus | None = None,
    ) -> list[TaskRead]:
        usage = _task_usage_subquery()
        stmt = (
            select(
                Task, Agent.code, Agent.name, WorkflowRun.project_id, Project.name,
                usage.c.input_tokens, usage.c.output_tokens, usage.c.cost_usd,
            )
            .join(Agent, Agent.id == Task.agent_id)
            .join(WorkflowRun, WorkflowRun.id == Task.run_id)
            .join(Project, Project.id == WorkflowRun.project_id)
            .outerjoin(usage, usage.c.task_id == Task.id)
            .order_by(Task.run_id.desc(), Task.id)
            .limit(MAX_TASKS)
        )
        if project_id is not None:
            stmt = stmt.where(WorkflowRun.project_id == project_id)
        if run_id is not None:
            stmt = stmt.where(Task.run_id == run_id)
        if agent_code is not None:
            stmt = stmt.where(Agent.code == agent_code)
        if status is not None:
            stmt = stmt.where(Task.status == status)
        rows = self.db.execute(stmt).all()

        deps: dict[int, list[str]] = defaultdict(list)
        if rows:
            ids = [r[0].id for r in rows]
            dep_rows = self.db.execute(
                select(TaskDependency.task_id, Task.task_key)
                .join(Task, Task.id == TaskDependency.depends_on_task_id)
                .where(TaskDependency.task_id.in_(ids))
            )
            for task_id, key in dep_rows:
                deps[task_id].append(key)

        return [
            TaskRead(
                id=t.id, run_id=t.run_id, project_id=pid, project_name=pname,
                agent_code=code, agent_name=aname, task_key=t.task_key, title=t.title,
                description=t.description, status=t.status, attempt=t.attempt, max_attempts=t.max_attempts,
                error=t.error, depends_on=sorted(deps[t.id]),
                input_tokens=int(i or 0), output_tokens=int(o or 0), cost_usd=float(c or 0),
                started_at=t.started_at, finished_at=t.finished_at, created_at=t.created_at, updated_at=t.updated_at,
            )
            for t, code, aname, pid, pname, i, o, c in rows
        ]

    # ---- events (execution history) ----------------------------------------

    def list_events(
        self,
        project_id: int | None = None,
        run_id: int | None = None,
        agent_code: str | None = None,
        event_type: str | None = None,
        search: str | None = None,
        before_id: int | None = None,
        limit: int = 50,
    ) -> EventPage:
        base = (
            select(ExecutionEvent, WorkflowRun.project_id, Project.name, Task.title, Agent.code)
            .join(WorkflowRun, WorkflowRun.id == ExecutionEvent.run_id)
            .join(Project, Project.id == WorkflowRun.project_id)
            .outerjoin(Task, Task.id == ExecutionEvent.task_id)
            .outerjoin(Agent, Agent.id == Task.agent_id)
        )
        if project_id is not None:
            base = base.where(WorkflowRun.project_id == project_id)
        if run_id is not None:
            base = base.where(ExecutionEvent.run_id == run_id)
        if agent_code is not None:
            base = base.where(Agent.code == agent_code)
        if event_type is not None:
            base = base.where(ExecutionEvent.event_type == event_type)
        if search:
            # autoescape covers % and _; SQL Server LIKE also treats "[" as a character class
            base = base.where(ExecutionEvent.message.contains(search.replace("[", "[[]"), autoescape=True))

        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        page = base.order_by(ExecutionEvent.id.desc()).limit(limit + 1)
        if before_id is not None:
            page = page.where(ExecutionEvent.id < before_id)
        rows = self.db.execute(page).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        items = [
            EventRead(
                id=e.id, run_id=e.run_id, project_id=pid, project_name=pname, task_id=e.task_id,
                task_title=ttitle, agent_code=code, event_type=e.event_type, message=e.message,
                data=e.data, created_at=e.created_at,
            )
            for e, pid, pname, ttitle, code in rows
        ]
        return EventPage(items=items, total=total, next_before_id=items[-1].id if has_more else None)

    # ---- approvals ----------------------------------------------------------

    def _approval_stmt(self):
        return (
            select(Approval, WorkflowRun.project_id, Project.name, Agent.code)
            .join(WorkflowRun, WorkflowRun.id == Approval.run_id)
            .join(Project, Project.id == WorkflowRun.project_id)
            .outerjoin(Task, Task.id == Approval.task_id)
            .outerjoin(Agent, Agent.id == Task.agent_id)
        )

    @staticmethod
    def _approval(a: Approval, project_id: int, project_name: str, agent_code: str | None) -> ApprovalRead:
        return ApprovalRead(
            id=a.id, run_id=a.run_id, project_id=project_id, project_name=project_name, task_id=a.task_id,
            agent_code=agent_code, kind=a.kind, title=a.title, payload=a.payload, status=a.status,
            decision_note=a.decision_note, decided_at=a.decided_at, created_at=a.created_at,
        )

    def list_approvals(self, status: ApprovalStatus | None = None, limit: int = 200) -> list[ApprovalRead]:
        stmt = self._approval_stmt().order_by(Approval.id.desc()).limit(limit)
        if status is not None:
            stmt = stmt.where(Approval.status == status)
        return [self._approval(*row) for row in self.db.execute(stmt)]

    def decide(self, approval_id: int, approve: bool, note: str | None) -> ApprovalRead:
        approval = self.db.get(Approval, approval_id)
        if approval is None:
            raise NotFoundError(f"Approval {approval_id} not found")
        if approval.status != ApprovalStatus.PENDING:
            raise ConflictError(f"Approval {approval_id} was already {approval.status.value}")
        approval.status = ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED
        approval.decision_note = note
        approval.decided_at = datetime.now(UTC).replace(tzinfo=None)
        self.db.add(
            ExecutionEvent(
                run_id=approval.run_id,
                task_id=approval.task_id,
                event_type="approval.approved" if approve else "approval.rejected",
                message=f"{'Đã phê duyệt' if approve else 'Đã từ chối'}: {approval.title}",
                data={"approval_id": approval.id, "note": note},
            )
        )
        self.db.commit()
        result = self._approval(*self.db.execute(self._approval_stmt().where(Approval.id == approval_id)).one())
        payload = result.model_dump(mode="json")
        hub.publish_threadsafe("approvals", "approval.decided", payload)
        hub.publish_threadsafe(f"runs:{approval.run_id}", "approval.decided", payload)
        return result
