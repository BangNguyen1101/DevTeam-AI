from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Unicode, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, DateTime2


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(Unicode(100), unique=True, nullable=False)
    # "scrypt$n$r$p$salt_hex$hash_hex" (see app/core/security.py)
    password_hash: Mapped[str] = mapped_column(Unicode(300), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime2(), server_default=func.sysutcdatetime(), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime2())


class UserSession(Base):
    """Server-side session; the browser only holds the random token in an httpOnly cookie."""

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    # SHA-256 of the token: a DB leak does not reveal usable cookies
    token_hash: Mapped[str] = mapped_column(Unicode(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime2(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime2(), server_default=func.sysutcdatetime(), nullable=False)
