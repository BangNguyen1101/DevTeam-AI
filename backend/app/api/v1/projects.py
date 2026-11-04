import asyncio

from fastapi import APIRouter, Query, status
from pydantic import BaseModel

from app.ai_core.execution.preview import previews
from app.api.deps import DbSession, Workspaces
from app.models.enums import ProjectStatus
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services import workspace_files
from app.services.project import ProjectService
from app.services.workspace_files import FileContent, FileEntry

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(db: DbSession, workspaces: Workspaces, status: ProjectStatus | None = None):
    return ProjectService(db, workspaces).list(status)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, db: DbSession, workspaces: Workspaces):
    return ProjectService(db, workspaces).create(data)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: DbSession, workspaces: Workspaces):
    return ProjectService(db, workspaces).get(project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, data: ProjectUpdate, db: DbSession, workspaces: Workspaces):
    return ProjectService(db, workspaces).update(project_id, data)


class PreviewStatus(BaseModel):
    running: bool
    url: str | None = None
    api_running: bool = False
    started_at: float | None = None
    log_tail: str | None = None


def _preview_status(project_id: int) -> PreviewStatus:
    p = previews.get(project_id)
    if p is None:
        return PreviewStatus(running=False)
    return PreviewStatus(running=True, url=f"/preview/{p.token}/", api_running=p.api_running,
                         started_at=p.started_at, log_tail=p.log_tail() or None)


@router.get("/{project_id}/preview", response_model=PreviewStatus)
def preview_status(project_id: int, db: DbSession, workspaces: Workspaces):
    ProjectService(db, workspaces).get(project_id)
    return _preview_status(project_id)


@router.post("/{project_id}/preview", response_model=PreviewStatus)
async def start_preview(project_id: int, db: DbSession, workspaces: Workspaces):
    """Explicit user action: runs the AI-generated backend of this project on this machine."""
    project = ProjectService(db, workspaces).get(project_id)
    await asyncio.to_thread(previews.start, project.id, workspaces.project_root(project.workspace_dir))
    return _preview_status(project_id)


@router.delete("/{project_id}/preview", status_code=status.HTTP_204_NO_CONTENT)
def stop_preview(project_id: int):
    previews.stop(project_id)


@router.get("/{project_id}/files", response_model=list[FileEntry])
def list_project_files(project_id: int, db: DbSession, workspaces: Workspaces):
    project = ProjectService(db, workspaces).get(project_id)
    return workspace_files.list_files(workspaces, project.workspace_dir)


@router.get("/{project_id}/files/content", response_model=FileContent)
def read_project_file(project_id: int, db: DbSession, workspaces: Workspaces, path: str = Query(..., max_length=500)):
    project = ProjectService(db, workspaces).get(project_id)
    return workspace_files.read_file(workspaces, project.workspace_dir, path)
