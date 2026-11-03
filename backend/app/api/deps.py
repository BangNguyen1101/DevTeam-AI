from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.ai_core.workspace.manager import WorkspaceManager
from app.core.config import get_settings
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]


def get_workspace_manager() -> WorkspaceManager:
    return WorkspaceManager(get_settings().workspaces_path)


Workspaces = Annotated[WorkspaceManager, Depends(get_workspace_manager)]
