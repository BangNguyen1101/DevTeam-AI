from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, Unicode, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, DateTime2, JsonText


class AppSetting(Base):
    """Key/value system configuration (model pricing, default budget, limits...)."""

    __tablename__ = "app_settings"
    __table_args__ = (CheckConstraint("ISJSON(value) = 1", name="value_json"),)

    key: Mapped[str] = mapped_column(Unicode(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JsonText, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime2(), server_default=func.sysutcdatetime(), onupdate=func.sysutcdatetime(), nullable=False
    )
