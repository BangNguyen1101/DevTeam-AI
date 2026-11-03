from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Project
from app.models.enums import ProjectStatus


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, project_id: int) -> Project | None:
        return self.db.get(Project, project_id)

    def get_by_name(self, name: str) -> Project | None:
        return self.db.scalar(select(Project).where(Project.name == name))

    def list(self, status: ProjectStatus | None = None) -> list[Project]:
        stmt = select(Project).order_by(Project.created_at.desc(), Project.id.desc())
        if status is not None:
            stmt = stmt.where(Project.status == status)
        return list(self.db.scalars(stmt))

    def add(self, project: Project) -> Project:
        self.db.add(project)
        self.db.flush()
        return project
