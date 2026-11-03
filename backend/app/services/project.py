import logging

from sqlalchemy.orm import Session

from app.ai_core.workspace.manager import WorkspaceManager, make_workspace_dir_name
from app.core.exceptions import ConflictError, NotFoundError
from app.models import Project
from app.models.enums import ProjectStatus
from app.realtime.hub import hub
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

logger = logging.getLogger(__name__)

TOPIC = "projects"


class ProjectService:
    def __init__(self, db: Session, workspaces: WorkspaceManager):
        self.db = db
        self.repo = ProjectRepository(db)
        self.workspaces = workspaces

    def list(self, status: ProjectStatus | None = None) -> list[Project]:
        return self.repo.list(status)

    def get(self, project_id: int) -> Project:
        project = self.repo.get(project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found")
        return project

    def create(self, data: ProjectCreate) -> Project:
        if self.repo.get_by_name(data.name):
            raise ConflictError(f"Project name '{data.name}' already exists")
        project = self.repo.add(
            Project(name=data.name, description=data.description, workspace_dir=make_workspace_dir_name(data.name))
        )
        # Create the folder before committing so a filesystem error rolls back the row
        self.workspaces.create(project.workspace_dir)
        self.db.commit()
        self.db.refresh(project)
        logger.info("Created project %s (%s)", project.id, project.workspace_dir)
        self._publish("project.created", project)
        return project

    def update(self, project_id: int, data: ProjectUpdate) -> Project:
        project = self.get(project_id)
        changes = data.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] != project.name and self.repo.get_by_name(changes["name"]):
            raise ConflictError(f"Project name '{changes['name']}' already exists")
        for field, value in changes.items():
            setattr(project, field, value)
        self.db.commit()
        self.db.refresh(project)
        self._publish("project.updated", project)
        return project

    def _publish(self, event_type: str, project: Project) -> None:
        hub.publish_threadsafe(TOPIC, event_type, ProjectRead.model_validate(project).model_dump(mode="json"))
