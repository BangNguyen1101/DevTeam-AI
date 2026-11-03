from sqlalchemy import BigInteger, Unicode, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import ProjectStatus, str_enum


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Unicode(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(UnicodeText)
    status: Mapped[ProjectStatus] = mapped_column(
        str_enum(ProjectStatus, "project_status"),
        default=ProjectStatus.ACTIVE,
        server_default=ProjectStatus.ACTIVE.value,
        nullable=False,
    )
    # Folder name under WORKSPACES_ROOT; never an absolute path
    workspace_dir: Mapped[str] = mapped_column(Unicode(100), unique=True, nullable=False)

    runs: Mapped[list["WorkflowRun"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
