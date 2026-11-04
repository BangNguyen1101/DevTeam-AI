import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.security import (
    DUMMY_HASH,
    MIN_PASSWORD_LENGTH,
    hash_password,
    hash_token,
    login_limiter,
    new_session_token,
    verify_password,
)
from app.models import User, UserSession

logger = logging.getLogger(__name__)

SESSION_COOKIE = "devteam_session"


class AuthError(AppError):
    status_code = 401
    code = "unauthorized"


class TooManyAttemptsError(AppError):
    status_code = 429
    code = "too_many_attempts"


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def login(self, username: str, password: str, client_ip: str) -> tuple[User, str, datetime]:
        keys = (f"user:{username.lower()}", f"ip:{client_ip}")
        if wait := login_limiter.retry_after(*keys):
            raise TooManyAttemptsError(f"Đăng nhập sai quá nhiều lần, thử lại sau {wait} giây")
        user = self.db.scalar(select(User).where(User.username == username))
        # Always run the hash so timing does not reveal whether the username exists
        valid = verify_password(password, user.password_hash if user else DUMMY_HASH) and user is not None
        if not valid:
            login_limiter.record_failure(*keys)
            logger.warning("Failed login for %r from %s", username, client_ip)
            raise AuthError("Sai tên đăng nhập hoặc mật khẩu")
        login_limiter.reset(*keys)

        token = new_session_token()
        expires = _now() + timedelta(hours=get_settings().session_hours)
        self.db.execute(delete(UserSession).where(UserSession.user_id == user.id, UserSession.expires_at < _now()))
        self.db.add(UserSession(user_id=user.id, token_hash=hash_token(token), expires_at=expires))
        user.last_login_at = _now()
        self.db.commit()
        return user, token, expires

    def user_for_token(self, token: str | None) -> User | None:
        if not token:
            return None
        return self.db.scalar(
            select(User).join(UserSession, UserSession.user_id == User.id)
            .where(UserSession.token_hash == hash_token(token), UserSession.expires_at > _now())
        )

    def logout(self, token: str | None) -> None:
        if token:
            self.db.execute(delete(UserSession).where(UserSession.token_hash == hash_token(token)))
            self.db.commit()

    def change_password(self, user: User, current: str, new: str) -> None:
        if not verify_password(current, user.password_hash):
            raise AuthError("Mật khẩu hiện tại không đúng")
        validate_password(new)
        user.password_hash = hash_password(new)
        # Sign out every other session of this user
        self.db.execute(delete(UserSession).where(UserSession.user_id == user.id))
        self.db.commit()


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AppError(f"Mật khẩu phải có ít nhất {MIN_PASSWORD_LENGTH} ký tự")


def ensure_admin(db: Session) -> None:
    """Create the first admin from ADMIN_USERNAME / ADMIN_PASSWORD when no user exists."""
    if db.scalar(select(func.count()).select_from(User)):
        return
    config = get_settings()
    password = config.admin_password.get_secret_value()
    if not password:
        logger.warning("No users and ADMIN_PASSWORD is empty: nobody can log in until it is set")
        return
    validate_password(password)
    db.add(User(username=config.admin_username, password_hash=hash_password(password)))
    db.commit()
    logger.info("Created admin account %r", config.admin_username)
