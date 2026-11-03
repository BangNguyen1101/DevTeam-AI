"""Read APIs over workflow data. Rows are inserted directly as the engine would."""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import Agent, Approval, ExecutionEvent, LlmUsage, Task, TaskDependency, WorkflowRun


@pytest.fixture
def run_data(client, db):
    project = client.post("/api/v1/projects", json={"name": "Read API"}).json()
    agents = {a.code: a.id for a in db.scalars(select(Agent))}
    run = WorkflowRun(project_id=project["id"], request_text="Ứng dụng ghi chú", status="running")
    db.add(run)
    db.flush()
    ba = Task(run_id=run.id, agent_id=agents["business_analyst"], task_key="ba", title="Phân tích", status="completed")
    arch = Task(run_id=run.id, agent_id=agents["architect"], task_key="arch", title="Thiết kế", status="running")
    db.add_all([ba, arch])
    db.flush()
    db.add_all([
        TaskDependency(task_id=arch.id, depends_on_task_id=ba.id),
        LlmUsage(run_id=run.id, task_id=ba.id, agent_id=agents["business_analyst"], model="m-small",
                 input_tokens=1000, output_tokens=500, cost_usd=Decimal("0.010000"), latency_ms=800),
        LlmUsage(run_id=run.id, task_id=arch.id, agent_id=agents["architect"], model="m-large",
                 input_tokens=2000, output_tokens=1000, cost_usd=Decimal("0.050000"), latency_ms=1200),
        ExecutionEvent(run_id=run.id, task_id=ba.id, event_type="task.completed", message="BA xong"),
        ExecutionEvent(run_id=run.id, task_id=arch.id, event_type="task.started", message="Architect bắt đầu"),
        ExecutionEvent(run_id=run.id, event_type="log", message="[TOOL] 100% done_ok"),
        Approval(run_id=run.id, task_id=arch.id, kind="command", title="Chạy lệnh lạ", payload={"cmd": "x"}),
    ])
    db.commit()
    return {"project": project, "run_id": run.id, "ba": ba.id, "arch": arch.id}


def test_run_detail_includes_tasks_dependencies_and_tokens(client, run_data):
    runs = client.get("/api/v1/runs", params={"project_id": run_data["project"]["id"]}).json()
    assert [r["id"] for r in runs] == [run_data["run_id"]]
    assert runs[0]["tasks_total"] == 2 and runs[0]["tasks_completed"] == 1

    detail = client.get(f"/api/v1/runs/{run_data['run_id']}").json()
    arch = next(t for t in detail["tasks"] if t["task_key"] == "arch")
    assert arch["depends_on"] == ["ba"]
    assert arch["agent_code"] == "architect"
    assert arch["input_tokens"] == 2000 and arch["cost_usd"] == pytest.approx(0.05)
    assert client.get("/api/v1/runs/999999999").status_code == 404


def test_task_filters(client, run_data):
    assert len(client.get("/api/v1/tasks", params={"run_id": run_data["run_id"]}).json()) == 2
    running = client.get("/api/v1/tasks", params={"status": "running", "run_id": run_data["run_id"]}).json()
    assert [t["task_key"] for t in running] == ["arch"]
    by_agent = client.get("/api/v1/tasks", params={"agent_code": "business_analyst", "run_id": run_data["run_id"]}).json()
    assert [t["task_key"] for t in by_agent] == ["ba"]


def test_events_paging_and_search(client, run_data):
    params = {"run_id": run_data["run_id"], "event_type": "task.started"}
    everything = client.get("/api/v1/events", params={"run_id": run_data["run_id"]}).json()
    assert everything["total"] == 3

    page = client.get("/api/v1/events", params={"run_id": run_data["run_id"], "limit": 2}).json()
    assert page["items"][0]["message"] == "[TOOL] 100% done_ok" and page["items"][0]["agent_code"] is None
    assert page["items"][1]["agent_code"] == "architect"
    nxt = client.get("/api/v1/events", params={"run_id": run_data["run_id"], "limit": 2,
                                               "before_id": page["next_before_id"]}).json()
    assert [e["message"] for e in nxt["items"]] == ["BA xong"] and nxt["next_before_id"] is None
    assert client.get("/api/v1/events", params=params).json()["total"] == 1

    def search(q: str) -> int:
        return client.get("/api/v1/events", params={"q": q, "run_id": run_data["run_id"]}).json()["total"]

    assert search("BA xong") == 1
    # LIKE metacharacters must be matched literally
    assert search("[TOOL]") == 1
    assert search("100%") == 1
    assert search("done_ok") == 1
    assert search("[A-Z]") == 0


def test_approval_decision_is_recorded_once(client, run_data):
    pending = client.get("/api/v1/approvals", params={"status": "pending"}).json()
    approval = next(a for a in pending if a["run_id"] == run_data["run_id"])
    assert approval["agent_code"] == "architect"

    with client.websocket_connect("/ws?topics=approvals") as ws:
        ws.receive_json()
        res = client.post(f"/api/v1/approvals/{approval['id']}/approve", json={"note": "ok"})
        assert res.status_code == 200 and res.json()["status"] == "approved"
        assert ws.receive_json()["type"] == "approval.decided"

    assert client.post(f"/api/v1/approvals/{approval['id']}/reject", json={}).status_code == 409
    events = client.get("/api/v1/events", params={"run_id": run_data["run_id"], "event_type": "approval.approved"}).json()
    assert events["total"] == 1


def test_usage_summary_and_dashboard(client, run_data):
    usage = client.get("/api/v1/usage/summary", params={"days": 7, "project_id": run_data["project"]["id"]}).json()
    assert usage["totals"]["total_tokens"] == 4500
    assert usage["totals"]["cost_usd"] == pytest.approx(0.06)
    assert [a["agent_code"] for a in usage["by_agent"]] == ["architect", "business_analyst"]
    assert {m["model"] for m in usage["by_model"]} == {"m-small", "m-large"}
    assert usage["by_project"][0]["tasks_completed"] == 0  # BA task has no finished_at
    assert len(usage["by_day"]) == 1

    dash = client.get("/api/v1/dashboard").json()
    assert dash["tasks_running"] >= 1 and dash["approvals_pending"] >= 1
    progress = next(p for p in dash["projects"] if p["project_id"] == run_data["project"]["id"])
    assert (progress["tasks_total"], progress["tasks_completed"]) == (2, 1)

    stats = {s["agent_code"]: s for s in client.get("/api/v1/agents/stats").json()}
    assert stats["architect"]["current_task_title"] == "Thiết kế"


def test_settings_roundtrip(client, restore_settings):
    s = client.get("/api/v1/settings").json()
    assert s["limits"]["max_task_attempts"] == 3
    limits = {**s["limits"], "monthly_budget_usd": 25}
    assert client.put("/api/v1/settings/limits", json=limits).json()["limits"]["monthly_budget_usd"] == 25
    assert client.put("/api/v1/settings/limits", json={**limits, "max_task_attempts": 0}).status_code == 422

    priced = client.put("/api/v1/settings/pricing", json={"m-small": {"input_per_1m": 0.25, "output_per_1m": 2}}).json()
    assert priced["pricing"]["m-small"]["output_per_1m"] == 2


def test_agent_update(client, db):
    agent_id = db.scalar(select(Agent.id).where(Agent.code == "qa_tester"))
    original = client.get("/api/v1/agents").json()
    before = next(a for a in original if a["id"] == agent_id)
    try:
        res = client.patch(f"/api/v1/agents/{agent_id}", json={"model": "custom-model", "is_enabled": False})
        assert res.status_code == 200
        assert res.json()["model"] == "custom-model" and res.json()["is_enabled"] is False
        assert "cmd.run" in res.json()["permissions"]
        assert client.patch(f"/api/v1/agents/{agent_id}", json={"max_output_tokens": 10}).status_code == 422
    finally:
        client.patch(f"/api/v1/agents/{agent_id}", json={"model": before["model"], "is_enabled": before["is_enabled"]})


def test_workspace_files(client, workspace_root):
    project = client.post("/api/v1/projects", json={"name": "Files"}).json()
    root = workspace_root / project["workspace_dir"]
    (root / "docs").mkdir()
    (root / "docs" / "SRS.md").write_text("# Đặc tả", encoding="utf-8")
    (root / "logo.bin").write_bytes(b"\x00\x01")

    files = client.get(f"/api/v1/projects/{project['id']}/files").json()
    assert [f["path"] for f in files] == ["docs", "docs/SRS.md", "logo.bin"]

    url = f"/api/v1/projects/{project['id']}/files/content"
    assert client.get(url, params={"path": "docs/SRS.md"}).json()["content"] == "# Đặc tả"
    assert client.get(url, params={"path": "logo.bin"}).status_code == 415
    assert client.get(url, params={"path": "../../secret"}).status_code == 403
    assert client.get(url, params={"path": "missing.md"}).status_code == 404
