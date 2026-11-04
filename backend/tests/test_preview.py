"""Live preview: real uvicorn subprocess for a generated app, served via /preview/{token}."""

from pathlib import Path

import pytest

from app.ai_core.execution.preview import previews

APP = """from fastapi import FastAPI
app = FastAPI()
ITEMS = []

@app.get("/items")
def items():
    return ITEMS

@app.post("/items", status_code=201)
def add(item: dict):
    ITEMS.append(item["name"])
    return {"count": len(ITEMS)}
"""
JS = "const API_URL = 'http://localhost:8001';\nfetch(`${API_URL}/items`);\n"


@pytest.fixture
def generated(client, workspace_root: Path):
    project = client.post("/api/v1/projects", json={"name": "Preview app"}).json()
    root = workspace_root / project["workspace_dir"]
    (root / "backend" / "app").mkdir(parents=True)
    (root / "backend" / "__init__.py").write_text("", encoding="utf-8")
    (root / "backend" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (root / "backend" / "app" / "main.py").write_text(APP, encoding="utf-8")
    (root / "frontend").mkdir()
    (root / "frontend" / "index.html").write_text("<h1>Xin chào</h1><script src='app.js'></script>", encoding="utf-8")
    (root / "frontend" / "app.js").write_text(JS, encoding="utf-8")
    yield project, root
    previews.stop_all()


def test_start_serve_proxy_and_stop(client, generated):
    project, _ = generated
    assert client.get(f"/api/v1/projects/{project['id']}/preview").json()["running"] is False

    status = client.post(f"/api/v1/projects/{project['id']}/preview").json()
    assert status["running"] and status["api_running"]
    url = status["url"]
    assert url.startswith("/preview/") and len(url) > 30

    page = client.get(url)
    assert page.status_code == 200 and "Xin chào" in page.text
    assert page.headers["content-security-policy"].startswith("sandbox allow-scripts")
    js = client.get(url + "app.js").text
    assert "http://localhost:8001" not in js and f"{url}api" in js  # rewired to the proxy

    assert client.post(url + "api/items", json={"name": "sách"}).json() == {"count": 1}
    listed = client.get(url + "api/items")
    assert listed.json() == ["sách"] and listed.headers["access-control-allow-origin"] == "*"
    assert client.options(url + "api/items").status_code == 204  # preflight from the sandboxed origin

    # Starting again reuses the running preview
    assert client.post(f"/api/v1/projects/{project['id']}/preview").json()["url"] == url

    assert client.delete(f"/api/v1/projects/{project['id']}/preview").status_code == 204
    assert client.get(url).status_code == 404
    assert client.get(f"/api/v1/projects/{project['id']}/preview").json()["running"] is False


def test_preview_does_not_leak_secrets_or_files(client, generated, monkeypatch):
    project, root = generated
    (root / "backend" / "app" / "main.py").write_text(
        "import os\nfrom fastapi import FastAPI\napp = FastAPI()\n"
        "@app.get('/env')\ndef env():\n    return sorted(k for k in os.environ if 'KEY' in k or 'PASSWORD' in k)\n",
        encoding="utf-8")
    monkeypatch.setenv("LLM_API_KEY", "secret")
    url = client.post(f"/api/v1/projects/{project['id']}/preview").json()["url"]
    assert client.get(url + "api/env").json() == []
    for bad in ("..%2Fbackend%2Fapp%2Fmain.py", "../backend/app/main.py", "%2e%2e/backend/app/main.py"):
        res = client.get(url + bad)
        assert res.status_code == 404 or "FastAPI" not in res.text


def test_preview_requires_login_but_page_uses_token(client, anon_client, generated):
    project, _ = generated
    url = client.post(f"/api/v1/projects/{project['id']}/preview").json()["url"]
    client.post("/api/v1/auth/logout")
    assert anon_client.post(f"/api/v1/projects/{project['id']}/preview").status_code == 401
    assert anon_client.get(url).status_code == 200  # the token is the capability
    assert anon_client.get("/preview/not-a-real-token/").status_code == 404


def test_broken_generated_backend_reports_its_error(client, generated):
    project, root = generated
    (root / "backend" / "app" / "main.py").write_text("raise RuntimeError('boom from generated app')\n", encoding="utf-8")
    res = client.post(f"/api/v1/projects/{project['id']}/preview")
    assert res.status_code == 409 and "boom from generated app" in res.json()["error"]["message"]
    assert client.get(f"/api/v1/projects/{project['id']}/preview").json()["running"] is False


def test_frontend_only_project_and_missing_frontend(client, generated):
    project, root = generated
    (root / "backend" / "app" / "main.py").unlink()
    status = client.post(f"/api/v1/projects/{project['id']}/preview").json()
    assert status["running"] and not status["api_running"]
    assert client.get(status["url"] + "api/items").status_code == 502
    previews.stop_all()
    (root / "frontend" / "index.html").unlink()
    res = client.post(f"/api/v1/projects/{project['id']}/preview")
    assert res.status_code == 409 and "index.html" in res.json()["error"]["message"]


def test_idle_previews_are_stopped(client, generated, monkeypatch):
    project, _ = generated
    url = client.post(f"/api/v1/projects/{project['id']}/preview").json()["url"]
    process = previews.get(project["id"]).process
    monkeypatch.setattr(previews, "idle_seconds", 0)
    assert client.get(url).status_code == 404
    process.wait(timeout=5)
    assert process.poll() is not None
