from datetime import datetime

from sqlalchemy import MetaData, func
from sqlalchemy.dialects import mssql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Fixed constraint names so Alembic migrations are deterministic on SQL Server
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# SQL Server specific column types used across models
DateTime2 = mssql.DATETIME2


class JsonText(mssql.JSON):
    """NVARCHAR(MAX) JSON; pair with an ISJSON check.

    Python None must become SQL NULL: the default would store the JSON literal
    'null', which SQL Server's ISJSON() rejects.
    """

    cache_ok = True

    def __init__(self, none_as_null: bool = True):
        super().__init__(none_as_null=none_as_null)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime2(), server_default=func.sysutcdatetime(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime2(),
        server_default=func.sysutcdatetime(),
        onupdate=func.sysutcdatetime(),
        nullable=False,
    )
