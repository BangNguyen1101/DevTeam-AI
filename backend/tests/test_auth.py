import pytest
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

from app.core.security import hash_password, hash_token, verify_password
from app.models import Approval, User, UserSession, WorkflowRun
from app.services.auth import SESSION_COOKIE
from tests.conftest import TEST_PASSWORD, TEST_USER, TestSession

PROTECTED = [
    ("GET", "/api/v1/projects"), ("POST", "/api/v1/projects"), ("GET", "/api/v1/agents"),
    ("PATCH", "/api/v1/agents/1"), ("GET", "/api/v1/dashboard"), ("GET", "/api/v1/settings"),
    ("PUT", "/api/v1/settings/limits"), ("GET", "/api/v1/runs"), ("GET", "/api/v1/events"),
    ("GET", "/api/v1/approvals"), ("POST", "/api/v1/approvals/1/approve"), ("POST", "/api/v1/projects/1/runs"),
    ("GET", "/api/v1/llm/models"), ("GET", "/api/v1/auth/me"),
]


def test_password_hashing():
    stored = hash_password("correct horse battery")
    assert stored.startswith("scrypt$") and "correct" not in stored
    assert verify_password("correct horse battery", stored)
    assert not verify_password("wrong", stored)
    assert not verify_password("x", "garbage")
    assert hash_password("same") != hash_password("same")  # random salt


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_api_requires_login(anon_client, method, path):
    res = anon_client.request(method, path, json={})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "unauthorized"


def test_health_is_public(anon_client):
    assert anon_client.get("/api/v1/health").status_code == 200


def test_login_sets_httponly_cookie_and_stores_only_token_hash(anon_client):
    res = anon_client.post("/api/v1/auth/login", json={"username": TEST_USER, "password": TEST_PASSWORD})
    assert res.status_code == 200 and res.json() == {"username": TEST_USER}
    cookie = res.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    token = anon_client.cookies[SESSION_COOKIE]
    with TestSession() as db:
        hashes = set(db.scalars(select(UserSession.token_hash)))
    assert hash_token(token) in hashes and token not in hashes
    assert anon_client.get("/api/v1/auth/me").json() == {"username": TEST_USER}


def test_wrong_credentials_are_indistinguishable(anon_client):
    bad_pw = anon_client.post("/api/v1/auth/login", json={"username": TEST_USER, "password": "nope"})
    no_user = anon_client.post("/api/v1/auth/login", json={"username": "ghost", "password": "nope"})
    assert bad_pw.status_code == no_user.status_code == 401
    assert bad_pw.json() == no_user.json()


def test_repeated_failures_are_rate_limited(anon_client):
    for _ in range(5):
        assert anon_client.post("/api/v1/auth/login", json={"username": TEST_USER, "password": "x"}).status_code == 401
    blocked = anon_client.post("/api/v1/auth/login", json={"username": TEST_USER, "password": TEST_PASSWORD})
    assert blocked.status_code == 429  # even the right password is refused while blocked
    assert blocked.json()["error"]["code"] == "too_many_attempts"


def test_logout_invalidates_session(client):
    token = client.cookies[SESSION_COOKIE]
    assert client.post("/api/v1/auth/logout").status_code == 204
    client.cookies.set(SESSION_COOKIE, token)  # replaying the old cookie must not work
    assert client.get("/api/v1/projects").status_code == 401


def test_expired_session_is_rejected(client):
    token = client.cookies[SESSION_COOKIE]
    with TestSession() as db:
        session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
        session.expires_at = session.created_at
        db.commit()
    assert client.get("/api/v1/projects").status_code == 401


def test_websocket_requires_login(anon_client, client):
    with pytest.raises(WebSocketDisconnect) as exc:
        with anon_client.websocket_connect("/ws?topics=projects", headers={"cookie": ""}) as ws:
            ws.receive_json()
    assert exc.value.code == 1008


def test_websocket_rejects_forged_cookie(anon_client):
    with pytest.raises(WebSocketDisconnect):
        with anon_client.websocket_connect("/ws?topics=projects", headers={"cookie": f"{SESSION_COOKIE}=forged"}) as ws:
            ws.receive_json()


def test_change_password(client):
    username = "pw-change-user"
    with TestSession() as db:
        db.add(User(username=username, password_hash=hash_password("old-password-1")))
        db.commit()
    try:
        assert client.post("/api/v1/auth/login", json={"username": username, "password": "old-password-1"}).status_code == 200
        short = client.post("/api/v1/auth/password", json={"current_password": "old-password-1", "new_password": "short"})
        assert short.status_code == 400
        wrong = client.post("/api/v1/auth/password", json={"current_password": "nope", "new_password": "new-password-2"})
        assert wrong.status_code == 401
        ok = client.post("/api/v1/auth/password", json={"current_password": "old-password-1", "new_password": "new-password-2"})
        assert ok.status_code == 204
        assert client.get("/api/v1/auth/me").status_code == 401  # all sessions signed out
        assert client.post("/api/v1/auth/login", json={"username": username, "password": "new-password-2"}).status_code == 200
    finally:
        with TestSession() as db:
            db.delete(db.scalar(select(User).where(User.username == username)))
            db.commit()


def test_approval_records_who_decided(client):
    project = client.post("/api/v1/projects", json={"name": "Auth audit"}).json()
    with TestSession() as db:
        run = WorkflowRun(project_id=project["id"], request_text="x" * 12, status="waiting_approval")
        db.add(run)
        db.flush()
        approval = Approval(run_id=run.id, kind="command", title="pytest")
        db.add(approval)
        db.commit()
        approval_id = approval.id
    res = client.post(f"/api/v1/approvals/{approval_id}/approve", json={})
    assert res.status_code == 200 and res.json()["decided_by"] == TEST_USER
