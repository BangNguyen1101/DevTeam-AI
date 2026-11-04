"""Tests run against the real SQL Server test database (DB_TEST_NAME), never SQLite.

Prepare once:  alembic -x db=DevTeamAI_Test upgrade head
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.ai_core.orchestrator import registry
from app.ai_core.workspace.manager import WorkspaceManager
from app.api.deps import get_workspace_manager
from app.core.config import get_settings
from app.core.security import hash_password, login_limiter
from app.db.session import build_engine, get_db
from app.main import app
from app.models import User
from app.realtime.routes import get_session_factory

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


TEST_USER, TEST_PASSWORD = "tester", "test-password-123"


@pytest.fixture(scope="session", autouse=True)
def _test_user(_check_test_database) -> None:
    with TestSession() as db:
        if not db.scalar(select(User).where(User.username == TEST_USER)):
            db.add(User(username=TEST_USER, password_hash=hash_password(TEST_PASSWORD)))
            db.commit()


@pytest.fixture
def anon_client(workspace_root: Path) -> Iterator[TestClient]:
    """Client without a session cookie."""
    workspace_root.mkdir(exist_ok=True)

    def _get_db() -> Iterator[Session]:
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    login_limiter.reset(f"user:{TEST_USER}", "ip:testclient")
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_workspace_manager] = lambda: WorkspaceManager(workspace_root)
    app.dependency_overrides[get_session_factory] = lambda: TestSession
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client(anon_client: TestClient) -> TestClient:
    """Client signed in as the test user (cookie kept by the client)."""
    res = anon_client.post("/api/v1/auth/login", json={"username": TEST_USER, "password": TEST_PASSWORD})
    assert res.status_code == 200, res.text
    return anon_client
