from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.ai_core.llm import provider
from app.ai_core.orchestrator import registry
from app.ai_core.orchestrator.engine import WorkflowEngine
from app.api.deps import CurrentUser, DbSession
from app.models.enums import ApprovalStatus, RunStatus, TaskStatus
from app.schemas.workflow import (
    ApprovalDecision,
    ApprovalRead,
    ArtifactRead,
    EventPage,
    RunCreate,
    RunDetail,
    RunRead,
    TaskRead,
)
from app.services.run import RunService
from app.services.workflow_query import WorkflowQueryService

router = APIRouter(tags=["workflow"])


def get_engine() -> WorkflowEngine:
    return registry.default_engine()


@router.post("/projects/{project_id}/runs", response_model=RunRead, status_code=status.HTTP_201_CREATED)
async def create_run(project_id: int, data: RunCreate, db: DbSession,
                     engine: Annotated[WorkflowEngine, Depends(get_engine)]):
    run = RunService(db).create(project_id, data.request_text, data.budget_usd)
    registry.start_run(run.id, engine)
    return WorkflowQueryService(db).get_run(run.id)


@router.post("/runs/{run_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
def cancel_run(run_id: int, db: DbSession):
    RunService(db).cancel(run_id)


@router.get("/llm/models", response_model=list[str])
async def list_llm_models():
    """Models the configured provider exposes (to pick agent models in Settings)."""
    return await provider.list_models()


@router.get("/runs", response_model=list[RunRead])
def list_runs(db: DbSession, project_id: int | None = None, status: RunStatus | None = None,
              limit: int = Query(100, ge=1, le=500)):
    return WorkflowQueryService(db).list_runs(project_id, status, limit)


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run(run_id: int, db: DbSession):
    return WorkflowQueryService(db).get_run(run_id)


@router.get("/runs/{run_id}/artifacts", response_model=list[ArtifactRead])
def list_artifacts(run_id: int, db: DbSession):
    return WorkflowQueryService(db).list_artifacts(run_id)


@router.get("/tasks", response_model=list[TaskRead])
def list_tasks(db: DbSession, project_id: int | None = None, run_id: int | None = None,
               agent_code: str | None = None, status: TaskStatus | None = None):
    return WorkflowQueryService(db).list_tasks(project_id, run_id, agent_code, status)


@router.get("/events", response_model=EventPage)
def list_events(db: DbSession, project_id: int | None = None, run_id: int | None = None,
                agent_code: str | None = None, event_type: str | None = None,
                q: str | None = Query(None, max_length=200), before_id: int | None = None,
                limit: int = Query(50, ge=1, le=200)):
    return WorkflowQueryService(db).list_events(project_id, run_id, agent_code, event_type, q, before_id, limit)


@router.get("/approvals", response_model=list[ApprovalRead])
def list_approvals(db: DbSession, status: ApprovalStatus | None = None):
    return WorkflowQueryService(db).list_approvals(status)


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalRead)
def approve(approval_id: int, data: ApprovalDecision, db: DbSession, user: CurrentUser):
    return WorkflowQueryService(db).decide(approval_id, True, data.note, decided_by=user.username)


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalRead)
def reject(approval_id: int, data: ApprovalDecision, db: DbSession, user: CurrentUser):
    return WorkflowQueryService(db).decide(approval_id, False, data.note, decided_by=user.username)
