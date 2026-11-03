"""Aggregations over llm_usage / tasks / runs for Dashboard, Agents and Usage pages."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import Date, case, cast, func, select
from sqlalchemy.orm import Session

from app.models import Agent, Approval, LlmUsage, Project, Task, WorkflowRun
from app.models.enums import ApprovalStatus, ProjectStatus, RunStatus, TaskStatus
from app.schemas.analytics import (
    AgentStats,
    AgentUsage,
    DailyUsage,
    DashboardSummary,
    ModelUsage,
    ProjectProgress,
    ProjectUsage,
    UsageSummary,
    UsageTotals,
)
from app.services.settings import SettingsService

ACTIVE_RUN_STATUSES = (RunStatus.PENDING, RunStatus.PLANNING, RunStatus.RUNNING, RunStatus.WAITING_APPROVAL)


def _utcnow() -> datetime:
    # DATETIME2 columns hold naive UTC
    return datetime.now(UTC).replace(tzinfo=None)


def _tokens():
    return func.coalesce(func.sum(LlmUsage.input_tokens + LlmUsage.output_tokens), 0)


def _cost():
    return func.coalesce(func.sum(LlmUsage.cost_usd), 0)


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def _month_cost(self) -> float:
        start = _utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return float(self.db.scalar(select(_cost()).where(LlmUsage.created_at >= start)))

    def usage_summary(self, days: int, project_id: int | None = None) -> UsageSummary:
        since = _utcnow() - timedelta(days=days)
        scope = [LlmUsage.created_at >= since]
        if project_id is not None:
            scope.append(LlmUsage.run_id.in_(select(WorkflowRun.id).where(WorkflowRun.project_id == project_id)))

        t = self.db.execute(
            select(
                func.count(),
                func.coalesce(func.sum(LlmUsage.request_count), 0),
                func.coalesce(func.sum(LlmUsage.input_tokens), 0),
                func.coalesce(func.sum(LlmUsage.cached_input_tokens), 0),
                func.coalesce(func.sum(LlmUsage.output_tokens), 0),
                _cost(),
            ).where(*scope)
        ).one()
        totals = UsageTotals(
            calls=t[0], requests=int(t[1]), input_tokens=int(t[2]), cached_input_tokens=int(t[3]),
            output_tokens=int(t[4]), total_tokens=int(t[2]) + int(t[4]), cost_usd=float(t[5]),
        )

        by_agent = [
            AgentUsage(agent_code=code, agent_name=name, calls=calls, total_tokens=int(tok), cost_usd=float(cost),
                       avg_latency_ms=float(lat) if lat is not None else None)
            for code, name, calls, tok, cost, lat in self.db.execute(
                select(Agent.code, Agent.name, func.count(), _tokens(), _cost(), func.avg(LlmUsage.latency_ms * 1.0))
                .join(Agent, Agent.id == LlmUsage.agent_id)
                .where(*scope)
                .group_by(Agent.id, Agent.code, Agent.name)
                .order_by(_cost().desc())
            )
        ]

        day = cast(LlmUsage.created_at, Date)
        by_day = [
            DailyUsage(day=d, total_tokens=int(tok), cost_usd=float(cost), calls=calls)
            for d, tok, cost, calls in self.db.execute(
                select(day, _tokens(), _cost(), func.count()).where(*scope).group_by(day).order_by(day)
            )
        ]

        by_model = [
            ModelUsage(model=m, calls=calls, total_tokens=int(tok), cost_usd=float(cost),
                       avg_latency_ms=float(lat) if lat is not None else None)
            for m, calls, tok, cost, lat in self.db.execute(
                select(LlmUsage.model, func.count(), _tokens(), _cost(), func.avg(LlmUsage.latency_ms * 1.0))
                .where(*scope)
                .group_by(LlmUsage.model)
                .order_by(_cost().desc())
            )
        ]

        completed = (
            select(WorkflowRun.project_id, func.count().label("n"))
            .join(Task, Task.run_id == WorkflowRun.id)
            .where(Task.status == TaskStatus.COMPLETED, Task.finished_at >= since)
            .group_by(WorkflowRun.project_id)
            .subquery()
        )
        usage_by_project = (
            select(WorkflowRun.project_id.label("project_id"), _tokens().label("tok"), _cost().label("cost"))
            .join(WorkflowRun, WorkflowRun.id == LlmUsage.run_id)
            .where(*scope)
            .group_by(WorkflowRun.project_id)
            .subquery()
        )
        project_stmt = (
            select(Project.id, Project.name, completed.c.n, usage_by_project.c.tok, usage_by_project.c.cost)
            .outerjoin(completed, completed.c.project_id == Project.id)
            .outerjoin(usage_by_project, usage_by_project.c.project_id == Project.id)
            .where((completed.c.n.is_not(None)) | (usage_by_project.c.tok.is_not(None)))
            .order_by(usage_by_project.c.cost.desc())
        )
        if project_id is not None:
            project_stmt = project_stmt.where(Project.id == project_id)
        by_project = [
            ProjectUsage(project_id=pid, project_name=name, tasks_completed=int(n or 0),
                         total_tokens=int(tok or 0), cost_usd=float(cost or 0))
            for pid, name, n, tok, cost in self.db.execute(project_stmt)
        ]

        return UsageSummary(
            days=days, totals=totals, by_agent=by_agent, by_day=by_day, by_model=by_model, by_project=by_project,
            monthly_budget_usd=SettingsService(self.db).limits().monthly_budget_usd,
            month_cost_usd=self._month_cost(),
        )

    def agent_stats(self) -> list[AgentStats]:
        task_counts = {
            agent_id: (total, done, failed)
            for agent_id, total, done, failed in self.db.execute(
                select(
                    Task.agent_id,
                    func.count(),
                    func.sum(case((Task.status == TaskStatus.COMPLETED, 1), else_=0)),
                    func.sum(case((Task.status == TaskStatus.FAILED, 1), else_=0)),
                ).group_by(Task.agent_id)
            )
        }
        usage = {
            agent_id: (int(tok), float(cost), last)
            for agent_id, tok, cost, last in self.db.execute(
                select(LlmUsage.agent_id, _tokens(), _cost(), func.max(LlmUsage.created_at)).group_by(LlmUsage.agent_id)
            )
        }
        # Latest running / waiting task per agent
        current: dict[int, tuple[str, str]] = {}
        for agent_id, title, status in self.db.execute(
            select(Task.agent_id, Task.title, Task.status)
            .where(Task.status.in_([TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL]))
            .order_by(Task.updated_at.desc())
        ):
            current.setdefault(agent_id, (title, status.value))

        result = []
        for agent in self.db.scalars(select(Agent).order_by(Agent.id)):
            total, done, failed = task_counts.get(agent.id, (0, 0, 0))
            tok, cost, last = usage.get(agent.id, (0, 0.0, None))
            title, status = current.get(agent.id, (None, None))
            result.append(
                AgentStats(
                    agent_id=agent.id, agent_code=agent.code, tasks_total=total, tasks_completed=int(done or 0),
                    tasks_failed=int(failed or 0), current_task_title=title, current_task_status=status,
                    total_tokens=tok, cost_usd=cost, last_active_at=last.isoformat() if last else None,
                )
            )
        return result

    def dashboard(self) -> DashboardSummary:
        projects_total, projects_active = self.db.execute(
            select(func.count(), func.sum(case((Project.status == ProjectStatus.ACTIVE, 1), else_=0)))
        ).one()
        running, completed, failed = self.db.execute(
            select(
                func.sum(case((Task.status == TaskStatus.RUNNING, 1), else_=0)),
                func.sum(case((Task.status == TaskStatus.COMPLETED, 1), else_=0)),
                func.sum(case((Task.status == TaskStatus.FAILED, 1), else_=0)),
            )
        ).one()
        completed, failed = int(completed or 0), int(failed or 0)
        agents_total, agents_enabled = self.db.execute(
            # SQL Server BIT is not a boolean expression; compare explicitly
            select(func.count(), func.sum(case((Agent.is_enabled == True, 1), else_=0)))  # noqa: E712
        ).one()
        tokens, cost = self.db.execute(select(_tokens(), _cost())).one()

        # Most recent run of each active project, with task progress
        latest = (
            select(WorkflowRun.project_id, func.max(WorkflowRun.id).label("run_id"))
            .group_by(WorkflowRun.project_id)
            .subquery()
        )
        counts = (
            select(
                Task.run_id,
                func.count().label("total"),
                func.sum(case((Task.status == TaskStatus.COMPLETED, 1), else_=0)).label("done"),
            )
            .group_by(Task.run_id)
            .subquery()
        )
        projects = [
            ProjectProgress(
                project_id=pid, project_name=name, latest_run_id=run_id,
                latest_run_status=status.value if status else None,
                tasks_total=int(total or 0), tasks_completed=int(done or 0),
            )
            for pid, name, run_id, status, total, done in self.db.execute(
                select(Project.id, Project.name, latest.c.run_id, WorkflowRun.status, counts.c.total, counts.c.done)
                .outerjoin(latest, latest.c.project_id == Project.id)
                .outerjoin(WorkflowRun, WorkflowRun.id == latest.c.run_id)
                .outerjoin(counts, counts.c.run_id == latest.c.run_id)
                .where(Project.status == ProjectStatus.ACTIVE)
                .order_by(Project.updated_at.desc())
            )
        ]

        return DashboardSummary(
            projects_total=projects_total,
            projects_active=int(projects_active or 0),
            runs_active=self.db.scalar(
                select(func.count()).select_from(WorkflowRun).where(WorkflowRun.status.in_(ACTIVE_RUN_STATUSES))
            ),
            tasks_running=int(running or 0),
            tasks_completed=completed,
            tasks_failed=failed,
            task_success_rate=completed / (completed + failed) if completed + failed else None,
            agents_enabled=int(agents_enabled or 0),
            agents_total=agents_total,
            total_tokens=int(tokens),
            cost_usd=float(cost),
            monthly_budget_usd=SettingsService(self.db).limits().monthly_budget_usd,
            approvals_pending=self.db.scalar(
                select(func.count()).select_from(Approval).where(Approval.status == ApprovalStatus.PENDING)
            ),
            projects=projects,
        )
