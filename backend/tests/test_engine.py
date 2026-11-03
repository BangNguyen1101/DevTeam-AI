"""Workflow Engine end to end with a scripted model (no network).

The model is fake; everything else is real: SQL Server rows, workspace files,
and pytest actually executing the generated tests through the Execution Engine.
"""

import asyncio
import json
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

import httpx
import openai
import pytest
from agents import Model, ModelResponse, Usage
from openai.types.responses import ResponseOutputMessage, ResponseOutputText
from sqlalchemy import select

from app.ai_core.execution.engine import CommandNotAllowedError, build_env, run_command
from app.ai_core.orchestrator.engine import WorkflowEngine
from app.ai_core.workspace.manager import WorkspaceManager
from app.models import Approval, Artifact, CommandExecution, ExecutionEvent, LlmUsage, Task, WorkflowRun
from app.schemas.analytics import Limits, ModelPrice
from app.services.settings import SettingsService
from app.services.workflow_query import WorkflowQueryService
from tests.conftest import TestSession

Responder = Callable[[str, str], dict]

APP_OK = """from fastapi import FastAPI
app = FastAPI()
NOTES: list[str] = []

@app.post("/notes", status_code=201)
def add(note: dict):
    NOTES.append(note["text"])
    return {"id": len(NOTES), "text": note["text"]}

@app.get("/notes")
def list_notes():
    return [{"id": i + 1, "text": t} for i, t in enumerate(NOTES)]
"""
APP_BUGGY = APP_OK.replace('status_code=201', 'status_code=200')
TESTS = """from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_and_list():
    res = client.post("/notes", json={"text": "xin chào"})
    assert res.status_code == 201
    assert client.get("/notes").json()[-1]["text"] == "xin chào"
"""


def plan(frontend: bool = False) -> dict:
    tasks = [
        {"key": "ba", "agent_code": "business_analyst", "title": "Phân tích", "description": "SRS", "depends_on": []},
        {"key": "arch", "agent_code": "architect", "title": "Thiết kế", "description": "API", "depends_on": ["ba"]},
        {"key": "be", "agent_code": "backend_dev", "title": "Backend", "description": "API ghi chú", "depends_on": ["arch"]},
        {"key": "qa", "agent_code": "qa_tester", "title": "Kiểm thử", "description": "pytest", "depends_on": ["be"]},
    ]
    if frontend:
        tasks.insert(3, {"key": "fe", "agent_code": "frontend_dev", "title": "Frontend", "description": "UI",
                         "depends_on": ["arch"]})
        tasks[-1]["depends_on"].append("fe")
    return {"analysis": "Ứng dụng ghi chú", "tasks": tasks}


def files(**contents: str) -> list[dict]:
    return [{"path": p.replace("__", "/").replace("_DOT_", "."), "content": c} for p, c in contents.items()]


def default_responder(backend_code: str = APP_OK, backend_path: str = "backend/app/main.py",
                      review_files: list[dict] | None = None) -> Responder:
    def respond(instructions: str, prompt: str) -> dict:
        if "tổng hợp kết quả" in instructions.lower():
            return {"summary": "Đã hoàn thành ứng dụng ghi chú."}
        if "Bộ test hiện đang đạt" in instructions:  # mandatory quality review
            assert "frontend/index.html" in prompt and "tests/test_notes.py" in prompt
            return {"root_cause": "Ổn", "issues": ["XSS"] if review_files else [], "summary": "review",
                    "files": review_files or []}
        if "tổng hợp kết quả" in instructions.lower():
            return {"summary": "Đã hoàn thành ứng dụng ghi chú."}
        if instructions.startswith("Bạn là AI Manager"):
            return plan(frontend=True)
        if instructions.startswith("Bạn là Business Analyst"):
            return {"filename": "SRS.md", "content": "# SRS\nGhi chú", "summary": "SRS ghi chú"}
        if instructions.startswith("Bạn là Software Architect"):
            return {"filename": "DESIGN.md", "content": "# DESIGN\nPOST /notes", "summary": "Thiết kế"}
        if instructions.startswith("Bạn là Backend Developer"):
            return {"summary": "API", "files": [
                {"path": "backend/__init__.py", "content": ""},
                {"path": "backend/app/__init__.py", "content": ""},
                {"path": backend_path, "content": backend_code},
            ]}
        if instructions.startswith("Bạn là Frontend Developer"):
            return {"summary": "UI", "files": [{"path": "frontend/index.html", "content": "<h1>Ghi chú</h1>"}]}
        if instructions.startswith("Bạn là QA Tester"):
            return {"summary": "Tests", "files": [{"path": "tests/__init__.py", "content": ""},
                                                  {"path": "tests/test_notes.py", "content": TESTS}]}
        if instructions.startswith("Bạn là Code Reviewer"):
            assert "status_code" in prompt  # reviewer sees the failing report and the code
            return {"root_cause": "Sai mã trạng thái", "issues": ["POST phải trả 201"], "summary": "Sửa 201",
                    "files": [{"path": "backend/app/main.py", "content": APP_OK}]}
        raise AssertionError(f"Unexpected agent: {instructions[:60]}")

    return respond


class FakeModel(Model):
    def __init__(self, responder: Responder, calls: list[str]):
        self.responder = responder
        self.calls = calls

    async def get_response(self, system_instructions, input, model_settings, tools, output_schema, handoffs,
                           tracing, *, previous_response_id=None, conversation_id=None, prompt=None):
        prompt_text = input if isinstance(input, str) else json.dumps(input, ensure_ascii=False)
        self.calls.append(system_instructions.split("\n", 1)[0])
        text = json.dumps(self.responder(system_instructions, prompt_text), ensure_ascii=False)
        message = ResponseOutputMessage(
            id="msg_1", type="message", role="assistant", status="completed",
            content=[ResponseOutputText(type="output_text", text=text, annotations=[])],
        )
        return ModelResponse(output=[message], usage=Usage(requests=1, input_tokens=1000, output_tokens=500,
                                                            total_tokens=1500), response_id=None)

    def stream_response(self, *args, **kwargs):
        raise NotImplementedError


@pytest.fixture
def project(client, workspace_root: Path) -> dict:
    p = client.post("/api/v1/projects", json={"name": "Engine test"}).json()
    p["root"] = workspace_root / p["workspace_dir"]
    return p


def make_engine(workspace_root: Path, responder: Responder, calls: list[str]) -> WorkflowEngine:
    return WorkflowEngine(TestSession, WorkspaceManager(workspace_root), lambda _name: FakeModel(responder, calls),
                          approval_poll_seconds=0.05, approval_timeout_seconds=30, llm_backoff=(0.01, 0.01))


def set_limits(**overrides) -> None:
    with TestSession() as db:
        svc = SettingsService(db)
        svc.update_limits(Limits(**{**svc.limits().model_dump(), **overrides}))


def new_run(project_id: int, budget: str | None = "5") -> int:
    with TestSession() as db:
        run = WorkflowRun(project_id=project_id, request_text="Ứng dụng ghi chú đơn giản", budget_usd=budget)
        db.add(run)
        db.commit()
        return run.id


def load(run_id: int):
    with TestSession() as db:
        run = db.get(WorkflowRun, run_id)
        tasks = {t.task_key: t for t in db.scalars(select(Task).where(Task.run_id == run_id))}
        return run, tasks


def test_full_pipeline_writes_code_and_passes_real_tests(project, workspace_root, restore_settings):
    set_limits(require_command_approval=False)
    with TestSession() as db:
        SettingsService(db).update_pricing({"gpt-5-mini": ModelPrice(input_per_1m=1, output_per_1m=2)})
    calls: list[str] = []
    run_id = new_run(project["id"])

    asyncio.run(make_engine(workspace_root, default_responder(), calls).run(run_id))

    run, tasks = load(run_id)
    assert run.status.value == "completed", run.error
    assert run.summary == "Đã hoàn thành ứng dụng ghi chú."
    # Tests passed -> mandatory review ran; it changed nothing, so no re-test was needed
    assert {k: t.status.value for k, t in tasks.items()} == {k: "completed" for k in ("ba", "arch", "be", "fe", "qa", "review")}
    assert tasks["qa"].output_data["tests_passed"] is True
    # Real files in the workspace
    root: Path = project["root"]
    assert (root / "docs" / "SRS.md").read_text("utf-8").startswith("# SRS")
    assert (root / "backend" / "app" / "main.py").exists() and (root / "frontend" / "index.html").exists()
    # Manager plan + summary, 5 workers, 1 review -> 8 model calls, each recorded with cost from pricing
    assert len(calls) == 8
    with TestSession() as db:
        usage = list(db.scalars(select(LlmUsage).where(LlmUsage.run_id == run_id)))
        cmd = db.scalar(select(CommandExecution).where(CommandExecution.run_id == run_id))
        kinds = set(db.scalars(select(Artifact.kind).where(Artifact.run_id == run_id)))
    assert len(usage) == 8
    # gpt-5-mini priced at $1 / $2 per 1M: 1000 in + 500 out = $0.002; unpriced gpt-5 stays $0
    costs = {(u.model, u.cost_usd) for u in usage}
    assert costs == {("gpt-5-mini", Decimal("0.002000")), ("gpt-5", Decimal("0.000000"))}
    assert cmd.exit_code == 0 and "1 passed" in cmd.stdout
    assert {"plan", "requirements", "design", "source_file", "test_file", "test_report", "review"} <= kinds
    assert run.total_input_tokens == 8000


def test_review_changes_are_retested_by_qa(project, workspace_root, restore_settings):
    set_limits(require_command_approval=False)
    safe_ui = {"path": "frontend/index.html", "content": "<h1 id='t'></h1><script>t.textContent='Ghi chú'</script>"}
    run_id = new_run(project["id"])
    asyncio.run(make_engine(workspace_root, default_responder(review_files=[safe_ui]), []).run(run_id))
    run, tasks = load(run_id)
    assert run.status.value == "completed", run.error
    assert tasks["review"].output_data["issues"] == ["XSS"]
    assert tasks["retest_review"].status.value == "completed"
    assert tasks["retest_review"].output_data["tests_passed"] is True
    assert "textContent" in (project["root"] / "frontend/index.html").read_text("utf-8")
    # Exactly one mandatory review per run
    assert [k for k in tasks if k.startswith("review")] == ["review"]


XSS_JS = "document.getElementById('t').innerHTML = `<b>${note.text}</b>`;\n"
SAFE_JS = "document.getElementById('t').textContent = note.text;\n"


def xss_responder(reviewer_fixes: bool) -> tuple[Responder, list[str]]:
    base = default_responder()
    review_prompts: list[str] = []

    def responder(instructions: str, prompt: str) -> dict:
        if instructions.startswith("Bạn là Frontend Developer"):
            return {"summary": "UI", "files": [{"path": "frontend/index.html", "content": "<p id='t'></p>"},
                                               {"path": "frontend/app.js", "content": XSS_JS}]}
        if "Bộ test hiện đang đạt" in instructions:
            review_prompts.append(prompt)
            files = [{"path": "frontend/app.js", "content": SAFE_JS}] if reviewer_fixes else []
            return {"root_cause": "ok", "issues": ["XSS"] if reviewer_fixes else [], "summary": "r", "files": files}
        return base(instructions, prompt)

    return responder, review_prompts


def test_static_scan_forces_reviewer_to_fix_xss(project, workspace_root, restore_settings):
    set_limits(require_command_approval=False)
    responder, review_prompts = xss_responder(reviewer_fixes=True)
    run_id = new_run(project["id"])
    asyncio.run(make_engine(workspace_root, responder, []).run(run_id))

    run, tasks = load(run_id)
    assert run.status.value == "completed", run.error
    assert "QUÉT TĨNH TỰ ĐỘNG" in review_prompts[0] and "xss-innerhtml" in review_prompts[0]
    assert tasks["review"].output_data["security_findings_before"] == 1
    assert tasks["review"].output_data["security_unresolved"] == []
    assert tasks["retest_review"].output_data["tests_passed"] is True
    assert (project["root"] / "frontend/app.js").read_text("utf-8") == SAFE_JS


def test_unfixed_security_findings_are_retried_then_reported(project, workspace_root, restore_settings):
    set_limits(require_command_approval=False, max_task_attempts=2)
    responder, review_prompts = xss_responder(reviewer_fixes=False)
    run_id = new_run(project["id"])
    asyncio.run(make_engine(workspace_root, responder, []).run(run_id))

    run, tasks = load(run_id)
    assert run.status.value == "completed", run.error
    assert tasks["review"].attempt == 2 and len(review_prompts) == 2
    assert "vẫn còn lỗi bảo mật" in review_prompts[1]  # second attempt is told what is left
    unresolved = tasks["review"].output_data["security_unresolved"]
    assert len(unresolved) == 1 and "frontend/app.js:1" in unresolved[0]
    with TestSession() as db:
        types = set(db.scalars(select(ExecutionEvent.event_type).where(ExecutionEvent.run_id == run_id)))
        review_doc = db.scalar(select(Artifact.content).where(Artifact.run_id == run_id, Artifact.kind == "review"))
    assert {"security.findings", "security.unresolved"} <= types
    assert "CHƯA XỬ LÝ" in review_doc


def test_stale_files_from_previous_run_can_be_deleted_within_area(project, workspace_root, restore_settings):
    """Seen in run #6: a previous run's tests/test_main.py no longer matched the rewritten backend."""
    set_limits(require_command_approval=False, mandatory_review=False)
    root: Path = project["root"]
    (root / "tests").mkdir()
    (root / "tests" / "test_old.py").write_text("def test_old():\n    assert False\n", encoding="utf-8")
    (root / "backend").mkdir()
    (root / "backend" / "legacy.py").write_text("x = 1\n", encoding="utf-8")
    base = default_responder()

    def responder(instructions: str, prompt: str) -> dict:
        out = base(instructions, prompt)
        if instructions.startswith("Bạn là QA Tester"):
            assert "Danh sách file hiện có trong workspace:" in prompt and "- tests/test_old.py" in prompt
            out["files"] += [{"path": "tests/test_old.py", "delete": True},
                             {"path": "backend/legacy.py", "delete": True}]  # outside QA's area
        return out

    run_id = new_run(project["id"])
    asyncio.run(make_engine(workspace_root, responder, []).run(run_id))
    run, tasks = load(run_id)
    assert run.status.value == "completed", tasks["qa"].error
    assert tasks["qa"].output_data["tests_passed"] is True
    assert not (root / "tests" / "test_old.py").exists()
    assert (root / "backend" / "legacy.py").exists()
    with TestSession() as db:
        events = {e.event_type: e.data for e in db.scalars(select(ExecutionEvent).where(ExecutionEvent.run_id == run_id))}
    assert events["files.deleted"] == {"files": ["tests/test_old.py"]}
    assert events["files.rejected"] == {"files": ["backend/legacy.py"]}


def test_mandatory_review_can_be_disabled(project, workspace_root, restore_settings):
    set_limits(require_command_approval=False, mandatory_review=False)
    run_id = new_run(project["id"])
    asyncio.run(make_engine(workspace_root, default_responder(), []).run(run_id))
    run, tasks = load(run_id)
    assert run.status.value == "completed", run.error
    assert "review" not in tasks


def test_failing_tests_trigger_reviewer_fix_and_retest(project, workspace_root, restore_settings):
    set_limits(require_command_approval=False, max_fix_iterations=2)
    run_id = new_run(project["id"])
    asyncio.run(make_engine(workspace_root, default_responder(APP_BUGGY), []).run(run_id))

    run, tasks = load(run_id)
    assert run.status.value == "completed", run.error
    assert tasks["qa"].output_data["tests_passed"] is False
    assert tasks["fix_1"].status.value == "completed"
    assert tasks["retest_1"].output_data["tests_passed"] is True
    assert "status_code=201" in (project["root"] / "backend/app/main.py").read_text("utf-8")


def test_tests_still_failing_after_fix_budget_fails_the_run(project, workspace_root, restore_settings):
    set_limits(require_command_approval=False, max_fix_iterations=0)
    run_id = new_run(project["id"])
    asyncio.run(make_engine(workspace_root, default_responder(APP_BUGGY), []).run(run_id))
    run, _ = load(run_id)
    assert run.status.value == "failed" and "Test vẫn lỗi" in run.error


def test_files_outside_agent_area_are_dropped_not_written(project, workspace_root, restore_settings):
    """Seen with Gemini: backend_dev also emits docs/ and tests/ files. Only backend/ may be written."""
    set_limits(require_command_approval=False)
    base = default_responder()

    def responder(instructions: str, prompt: str) -> dict:
        out = base(instructions, prompt)
        if instructions.startswith("Bạn là Backend Developer"):
            out["files"] += [{"path": "tests/evil.py", "content": "x"}, {"path": "docs/SRS.md", "content": "hijack"}]
        return out

    run_id = new_run(project["id"])
    asyncio.run(make_engine(workspace_root, responder, []).run(run_id))
    run, tasks = load(run_id)
    assert run.status.value == "completed", run.error
    assert "tests/evil.py" not in tasks["be"].output_data["files"]
    assert not (project["root"] / "tests" / "evil.py").exists()
    assert (project["root"] / "docs/SRS.md").read_text("utf-8").startswith("# SRS")
    with TestSession() as db:
        rejected = db.scalar(select(ExecutionEvent.data).where(ExecutionEvent.run_id == run_id,
                                                                ExecutionEvent.event_type == "files.rejected"))
    assert rejected == {"files": ["tests/evil.py", "docs/SRS.md"]}


def test_path_escaping_workspace_rejects_whole_change(project, workspace_root, restore_settings):
    set_limits(require_command_approval=False, max_task_attempts=2)
    run_id = new_run(project["id"])
    asyncio.run(make_engine(workspace_root, default_responder(backend_path="backend/../../escape.py"), []).run(run_id))
    run, tasks = load(run_id)
    assert run.status.value == "failed"
    assert tasks["be"].status.value == "failed" and tasks["be"].attempt == 2
    assert "escapes the workspace" in tasks["be"].error
    assert tasks["qa"].status.value == "skipped"
    assert not (workspace_root / "escape.py").exists()
    assert not (project["root"] / "backend" / "app" / "main.py").exists()  # nothing from that change set


def test_provider_overload_is_waited_out_without_using_task_attempts(project, workspace_root, restore_settings):
    """Real Gemini free tier returns 429/503 under load; those must not fail the task."""
    set_limits(require_command_approval=False, max_task_attempts=1)
    base = default_responder()
    failures = {"arch": 2}

    def responder(instructions: str, prompt: str) -> dict:
        if instructions.startswith("Bạn là Software Architect") and failures["arch"]:
            failures["arch"] -= 1
            raise openai.InternalServerError(
                "overloaded", response=httpx.Response(503, request=httpx.Request("POST", "http://llm")), body=None)
        return base(instructions, prompt)

    run_id = new_run(project["id"])
    asyncio.run(make_engine(workspace_root, responder, []).run(run_id))
    run, tasks = load(run_id)
    assert run.status.value == "completed", run.error
    assert tasks["arch"].attempt == 1
    with TestSession() as db:
        retries = db.scalars(select(ExecutionEvent.message).where(ExecutionEvent.run_id == run_id,
                                                                   ExecutionEvent.event_type == "llm.retry")).all()
    assert len(retries) == 2 and "InternalServerError" in retries[0]


def test_cancel_during_provider_backoff_stops_without_more_calls(project, workspace_root, restore_settings):
    set_limits(require_command_approval=False)
    base = default_responder()
    arch_calls = {"n": 0}
    run_id = new_run(project["id"])

    def responder(instructions: str, prompt: str) -> dict:
        if instructions.startswith("Bạn là Software Architect"):
            arch_calls["n"] += 1
            with TestSession() as db:  # user presses "Hủy run" while the provider is rate limiting
                db.get(WorkflowRun, run_id).status = "cancelled"
                db.commit()
            raise openai.RateLimitError(
                "busy", response=httpx.Response(429, request=httpx.Request("POST", "http://llm")), body=None)
        return base(instructions, prompt)

    asyncio.run(make_engine(workspace_root, responder, []).run(run_id))
    run, tasks = load(run_id)
    assert run.status.value == "cancelled"
    assert arch_calls["n"] == 1
    assert tasks["be"].status.value == "skipped"


def test_daily_quota_exhaustion_stops_run_with_clear_message(project, workspace_root, restore_settings):
    set_limits(require_command_approval=False)
    base = default_responder()

    def responder(instructions: str, prompt: str) -> dict:
        if instructions.startswith("Bạn là Software Architect"):
            raise openai.RateLimitError(
                "quota", response=httpx.Response(429, request=httpx.Request("POST", "http://llm")),
                body={"details": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]})
        return base(instructions, prompt)

    run_id = new_run(project["id"])
    asyncio.run(make_engine(workspace_root, responder, []).run(run_id))
    run, tasks = load(run_id)
    assert run.status.value == "failed" and "hết quota trong ngày" in run.error
    assert tasks["arch"].attempt == 1  # no pointless retries
    with TestSession() as db:
        assert not db.scalars(select(ExecutionEvent).where(ExecutionEvent.run_id == run_id,
                                                           ExecutionEvent.event_type == "llm.retry")).all()


def test_rejected_attempt_feeds_error_back_to_agent(project, workspace_root, restore_settings):
    set_limits(require_command_approval=False, max_task_attempts=2)
    base = default_responder()
    prompts_seen: list[str] = []

    def responder(instructions: str, prompt: str) -> dict:
        if instructions.startswith("Bạn là Backend Developer"):
            prompts_seen.append(prompt)
            if len(prompts_seen) == 1:  # first try writes outside its area, like Gemini did
                return {"summary": "x", "files": [{"path": "docs/SRS.md", "content": "overwrite"}]}
            assert "không có quyền ghi 'docs/SRS.md'" in prompt
        return base(instructions, prompt)

    run_id = new_run(project["id"])
    asyncio.run(make_engine(workspace_root, responder, []).run(run_id))
    run, tasks = load(run_id)
    assert run.status.value == "completed", run.error
    assert tasks["be"].attempt == 2 and len(prompts_seen) == 2
    assert (project["root"] / "docs/SRS.md").read_text("utf-8").startswith("# SRS")  # not overwritten


def test_running_tests_waits_for_human_approval(project, workspace_root, restore_settings):
    set_limits(require_command_approval=True)
    run_id = new_run(project["id"])
    engine = make_engine(workspace_root, default_responder(), [])

    async def scenario():
        job = asyncio.create_task(engine.run(run_id))
        approval_id = None
        for _ in range(200):
            await asyncio.sleep(0.05)
            with TestSession() as db:
                approval_id = db.scalar(select(Approval.id).where(Approval.run_id == run_id))
                run_status = db.get(WorkflowRun, run_id).status.value
            if approval_id:
                break
        assert approval_id and run_status == "waiting_approval"
        with TestSession() as db:
            WorkflowQueryService(db).decide(approval_id, approve=True, note="ok")
        await job

    asyncio.run(scenario())
    run, _ = load(run_id)
    assert run.status.value == "completed", run.error
    with TestSession() as db:
        assert db.scalar(select(CommandExecution.approval_id).where(CommandExecution.run_id == run_id)) is not None


def test_rejected_approval_stops_run(project, workspace_root, restore_settings):
    set_limits(require_command_approval=True)
    run_id = new_run(project["id"])
    engine = make_engine(workspace_root, default_responder(), [])

    async def scenario():
        job = asyncio.create_task(engine.run(run_id))
        while True:
            await asyncio.sleep(0.05)
            with TestSession() as db:
                approval_id = db.scalar(select(Approval.id).where(Approval.run_id == run_id))
            if approval_id:
                break
        with TestSession() as db:
            WorkflowQueryService(db).decide(approval_id, approve=False, note="không")
        await job

    asyncio.run(scenario())
    run, tasks = load(run_id)
    assert run.status.value == "failed" and "từ chối" in run.error
    with TestSession() as db:
        assert db.scalar(select(CommandExecution).where(CommandExecution.run_id == run_id)) is None


def test_invalid_plan_is_retried_with_feedback(project, workspace_root, restore_settings):
    set_limits(require_command_approval=False, max_task_attempts=2)
    attempts = {"n": 0}
    base = default_responder()

    def responder(instructions: str, prompt: str) -> dict:
        if instructions.startswith("Bạn là AI Manager") and "tổng hợp" not in instructions.lower():
            attempts["n"] += 1
            if attempts["n"] == 1:
                return {"analysis": "x", "tasks": [{"key": "be", "agent_code": "backend_dev", "title": "t",
                                                    "description": "d", "depends_on": ["be"]}]}
            assert "không hợp lệ" in prompt
        return base(instructions, prompt)

    run_id = new_run(project["id"])
    asyncio.run(make_engine(workspace_root, responder, []).run(run_id))
    run, _ = load(run_id)
    assert run.status.value == "completed", run.error
    assert attempts["n"] == 2


def test_budget_is_enforced(project, workspace_root, restore_settings):
    set_limits(require_command_approval=False)
    with TestSession() as db:
        SettingsService(db).update_pricing({"gpt-5": ModelPrice(input_per_1m=1000, output_per_1m=1000)})
    run_id = new_run(project["id"], budget="0.5")
    asyncio.run(make_engine(workspace_root, default_responder(), []).run(run_id))
    run, _ = load(run_id)
    assert run.status.value == "failed" and "Vượt ngân sách" in run.error


def test_execution_engine_allowlist_and_clean_env(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "secret-should-not-leak")
    with pytest.raises(CommandNotAllowedError):
        run_command("rm -rf /", tmp_path, 5)
    env = build_env(tmp_path)
    assert "LLM_API_KEY" not in env and env["PYTHONPATH"].endswith("backend")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_env.py").write_text(
        "import os\ndef test_no_secret():\n    assert 'LLM_API_KEY' not in os.environ\n", encoding="utf-8")
    result = run_command("pytest", tmp_path, 60)
    assert result.succeeded, result.stdout + result.stderr


def test_create_run_api(client, project, workspace_root, monkeypatch, restore_settings):
    from app.ai_core.llm import provider
    from app.api.v1 import workflow
    from app.main import app

    monkeypatch.setattr(provider, "llm_configured", lambda: False)
    monkeypatch.setattr("app.services.run.llm_configured", lambda: False)
    res = client.post(f"/api/v1/projects/{project['id']}/runs", json={"request_text": "Ứng dụng ghi chú đơn giản"})
    assert res.status_code == 503 and res.json()["error"]["code"] == "llm_not_configured"

    monkeypatch.setattr("app.services.run.llm_configured", lambda: True)
    set_limits(require_command_approval=False)
    app.dependency_overrides[workflow.get_engine] = lambda: make_engine(workspace_root, default_responder(), [])
    res = client.post(f"/api/v1/projects/{project['id']}/runs", json={"request_text": "Ứng dụng ghi chú đơn giản"})
    assert res.status_code == 201
    run_id = res.json()["id"]
    # A second run on the same project is refused while the first is active
    again = client.post(f"/api/v1/projects/{project['id']}/runs", json={"request_text": "Ứng dụng ghi chú đơn giản"})
    assert again.status_code == 409

    for _ in range(300):
        status = client.get(f"/api/v1/runs/{run_id}").json()["status"]
        if status in ("completed", "failed"):
            break
        client.portal.call(asyncio.sleep, 0.05)
    assert status == "completed"
    assert client.post(f"/api/v1/runs/{run_id}/cancel").status_code == 409


def test_iteration_request_shows_existing_code_to_dev_agents(project, workspace_root, restore_settings):
    """Run #8: frontend_dev rewrote app.js from scratch because it never saw the current file."""
    set_limits(require_command_approval=False, mandatory_review=False)
    root: Path = project["root"]
    (root / "frontend").mkdir()
    (root / "frontend" / "index.html").write_text("<ul id='books'></ul><!-- existing list -->", encoding="utf-8")
    base = default_responder()
    seen: dict[str, str] = {}

    def responder(instructions: str, prompt: str) -> dict:
        for role in ("Frontend Developer", "Backend Developer"):
            if instructions.startswith(f"Bạn là {role}"):
                seen[role] = prompt
        return base(instructions, prompt)

    run_id = new_run(project["id"])
    asyncio.run(make_engine(workspace_root, responder, []).run(run_id))
    assert load(run_id)[0].status.value == "completed"
    assert "=== frontend/index.html ===" in seen["Frontend Developer"] and "existing list" in seen["Frontend Developer"]
    assert "=== frontend/index.html ===" not in seen["Backend Developer"]  # only its own area's code


def test_cancel_closes_pending_approvals(client, project):
    with TestSession() as db:
        run = WorkflowRun(project_id=project["id"], request_text="Ứng dụng ghi chú", status="waiting_approval")
        db.add(run)
        db.flush()
        db.add(Approval(run_id=run.id, kind="command", title="pytest"))
        db.commit()
        run_id = run.id
    assert client.post(f"/api/v1/runs/{run_id}/cancel").status_code == 204
    approvals = [a for a in client.get("/api/v1/approvals").json() if a["run_id"] == run_id]
    assert [(a["status"], a["decision_note"]) for a in approvals] == [("rejected", "Run đã bị hủy")]


def test_failed_run_closes_its_pending_approval(project, workspace_root, restore_settings):
    set_limits(require_command_approval=True)
    run_id = new_run(project["id"])
    engine = WorkflowEngine(TestSession, WorkspaceManager(workspace_root), lambda _n: FakeModel(default_responder(), []),
                            approval_poll_seconds=0.05, approval_timeout_seconds=0.2, llm_backoff=(0.01,))
    asyncio.run(engine.run(run_id))
    run, _ = load(run_id)
    assert run.status.value == "failed" and "Hết thời gian chờ phê duyệt" in run.error
    with TestSession() as db:
        statuses = db.scalars(select(Approval.status).where(Approval.run_id == run_id)).all()
    assert [s.value for s in statuses] == ["rejected"]


def test_cancel_closes_unfinished_tasks_even_without_engine(client, project):
    with TestSession() as db:
        agent_id = db.scalar(select(Task.agent_id).limit(1)) or 1
        run = WorkflowRun(project_id=project["id"], request_text="Ứng dụng ghi chú", status="running")
        db.add(run)
        db.flush()
        db.add_all([Task(run_id=run.id, agent_id=agent_id, task_key="a", title="a", status="running"),
                    Task(run_id=run.id, agent_id=agent_id, task_key="b", title="b", status="completed")])
        db.commit()
        run_id = run.id
    assert client.post(f"/api/v1/runs/{run_id}/cancel").status_code == 204
    detail = client.get(f"/api/v1/runs/{run_id}").json()
    assert detail["status"] == "cancelled"
    assert {t["task_key"]: t["status"] for t in detail["tasks"]} == {"a": "skipped", "b": "completed"}
