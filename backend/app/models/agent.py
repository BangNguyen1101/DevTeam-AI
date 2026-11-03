from typing import Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Integer, Unicode, UnicodeText, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JsonText, TimestampMixin


class Agent(TimestampMixin, Base):
    """AI Manager and the 6 specialist agents. Configuration is editable at runtime."""

    __tablename__ = "agents"
    __table_args__ = (CheckConstraint("extra_params IS NULL OR ISJSON(extra_params) = 1", name="extra_params_json"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(Unicode(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    role_description: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    model: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    max_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, server_default=true(), nullable=False)
    instructions: Mapped[str | None] = mapped_column(UnicodeText)
    extra_params: Mapped[dict[str, Any] | None] = mapped_column(JsonText)

    permissions: Mapped[list["AgentPermission"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan", passive_deletes=True
    )


class AgentPermission(Base):
    """Capability granted to an agent, e.g. 'fs.read', 'fs.write:backend', 'cmd.run'."""

    __tablename__ = "agent_permissions"
    __table_args__ = (UniqueConstraint("agent_id", "permission"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    permission: Mapped[str] = mapped_column(Unicode(100), nullable=False)

    agent: Mapped[Agent] = relationship(back_populates="permissions")
