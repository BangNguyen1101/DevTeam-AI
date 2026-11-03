from pathlib import Path

from sqlalchemy import select

from app.models import Project


def test_health_reports_database(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["database"]["ok"] is True
    assert body["database"]["migration"]


def test_create_project_persists_row_and_workspace(client, db, workspace_root: Path):
    res = client.post("/api/v1/projects", json={"name": "Quản lý thư viện", "description": "Hệ thống mượn sách"})
    assert res.status_code == 201
    body = res.json()

    # Vietnamese text survives the round trip (NVARCHAR on a Latin1 collation)
    row = db.scalar(select(Project).where(Project.id == body["id"]))
    assert row is not None
    assert row.name == "Quản lý thư viện"
    assert row.description == "Hệ thống mượn sách"
    assert body["status"] == "active"
    assert body["workspace_dir"].startswith("quan-ly-thu-vien-")
    assert (workspace_root / body["workspace_dir"]).is_dir()


def test_duplicate_name_is_rejected(client):
    assert client.post("/api/v1/projects", json={"name": "Shop"}).status_code == 201
    res = client.post("/api/v1/projects", json={"name": "  Shop  "})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "conflict"


def test_blank_name_is_rejected(client):
    assert client.post("/api/v1/projects", json={"name": "   "}).status_code == 422


def test_list_filter_and_archive(client):
    a = client.post("/api/v1/projects", json={"name": "A"}).json()
    b = client.post("/api/v1/projects", json={"name": "B"}).json()

    res = client.patch(f"/api/v1/projects/{a['id']}", json={"status": "archived", "description": "done"})
    assert res.status_code == 200
    assert res.json()["status"] == "archived"
    assert res.json()["description"] == "done"

    active = client.get("/api/v1/projects", params={"status": "active"}).json()
    assert [p["id"] for p in active] == [b["id"]]
    assert {p["id"] for p in client.get("/api/v1/projects").json()} == {a["id"], b["id"]}


def test_rename_to_existing_name_conflicts(client):
    client.post("/api/v1/projects", json={"name": "A"})
    b = client.post("/api/v1/projects", json={"name": "B"}).json()
    assert client.patch(f"/api/v1/projects/{b['id']}", json={"name": "A"}).status_code == 409


def test_get_missing_project_returns_404(client):
    res = client.get("/api/v1/projects/999999999")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"


def test_agents_are_seeded_with_permissions(client):
    agents = client.get("/api/v1/agents").json()
    codes = [a["code"] for a in agents]
    assert codes == [
        "manager", "business_analyst", "architect", "backend_dev", "frontend_dev", "qa_tester", "code_reviewer",
    ]
    qa = next(a for a in agents if a["code"] == "qa_tester")
    assert "cmd.run" in qa["permissions"]
    ba = next(a for a in agents if a["code"] == "business_analyst")
    assert "cmd.run" not in ba["permissions"]
