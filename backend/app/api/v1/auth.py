from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.services.auth import SESSION_COOKIE, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)


class Me(BaseModel):
    username: str


@router.post("/login", response_model=Me)
def login(data: LoginRequest, request: Request, response: Response, db: DbSession):
    client_ip = request.client.host if request.client else "unknown"
    user, token, expires = AuthService(db).login(data.username.strip(), data.password, client_ip)
    response.set_cookie(
        SESSION_COOKIE, token,
        max_age=get_settings().session_hours * 3600,
        httponly=True,  # not readable from JavaScript
        samesite="strict",  # not sent on cross-site requests (CSRF)
        secure=get_settings().cookie_secure,
        path="/",
    )
    return Me(username=user.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbSession):
    AuthService(db).logout(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=Me)
def me(user: CurrentUser):
    return Me(username=user.username)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: PasswordChange, user: CurrentUser, response: Response, db: DbSession):
    AuthService(db).change_password(user, data.current_password, data.new_password)
    response.delete_cookie(SESSION_COOKIE, path="/")
