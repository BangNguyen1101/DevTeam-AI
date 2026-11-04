from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.ai_core.workspace.manager import WorkspaceManager
from app.core.config import get_settings
from app.db.session import get_db
from app.models import User
from app.services.auth import SESSION_COOKIE, AuthError, AuthService

DbSession = Annotated[Session, Depends(get_db)]


def get_workspace_manager() -> WorkspaceManager:
    return WorkspaceManager(get_settings().workspaces_path)


Workspaces = Annotated[WorkspaceManager, Depends(get_workspace_manager)]


def require_user(request: Request, db: DbSession) -> User:
    user = AuthService(db).user_for_token(request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise AuthError("Chưa đăng nhập hoặc phiên đã hết hạn")
    return user


CurrentUser = Annotated[User, Depends(require_user)]
