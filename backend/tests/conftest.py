"""Tests run against the real SQL Server test database (DB_TEST_NAME), never SQLite.

Prepare once:  alembic -x db=DevTeamAI_Test upgrade head
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.ai_core.orchestrator import registry
from app.ai_core.workspace.manager import WorkspaceManager
from app.api.deps import get_workspace_manager
from app.core.config import get_settings
from app.db.session import build_engine, get_db
from app.main import app

settings = get_settings()
test_engine = build_engine(settings.database_url(settings.db_test_name))
TestSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
registry.RECOVER_ON_STARTUP = False


@pytest.fixture
def restore_settings() -> Iterator[None]:
    with test_engine.connect() as conn:
        saved = conn.execute(text("SELECT [key], value FROM app_settings")).all()
    yield
    with test_engine.begin() as conn:
        conn.execute(text("DELETE FROM app_settings"))
        for key, value in saved:
            conn.execute(text("INSERT INTO app_settings ([key], value) VALUES (:k, :v)"), {"k": key, "v": value})


@pytest.fixture(scope="session", autouse=True)
def _check_test_database() -> None:
    with test_engine.connect() as conn:
        assert conn.execute(text("SELECT DB_NAME()")).scalar_one() == settings.db_test_name
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none(), (
            "Test DB not migrated: run `alembic -x db=DevTeamAI_Test upgrade head`"
        )


@pytest.fixture(autouse=True)
def _clean_tables() -> Iterator[None]:
    yield
    # Seeded tables (agents, app_settings) are kept; projects cascade to all run data
    with test_engine.begin() as conn:
        conn.execute(text("DELETE FROM projects"))


@pytest.fixture
def db() -> Iterator[Session]:
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    return tmp_path / "workspaces"


@pytest.fixture
def client(workspace_root: Path) -> Iterator[TestClient]:
    workspace_root.mkdir()

    def _get_db() -> Iterator[Session]:
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_workspace_manager] = lambda: WorkspaceManager(workspace_root)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
