from fastapi import APIRouter, Query, status

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


@router.get("/{project_id}/files", response_model=list[FileEntry])
def list_project_files(project_id: int, db: DbSession, workspaces: Workspaces):
    project = ProjectService(db, workspaces).get(project_id)
    return workspace_files.list_files(workspaces, project.workspace_dir)


@router.get("/{project_id}/files/content", response_model=FileContent)
def read_project_file(project_id: int, db: DbSession, workspaces: Workspaces, path: str = Query(..., max_length=500)):
    project = ProjectService(db, workspaces).get(project_id)
    return workspace_files.read_file(workspaces, project.workspace_dir, path)
