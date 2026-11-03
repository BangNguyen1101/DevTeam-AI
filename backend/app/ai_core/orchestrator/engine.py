"""Workflow Engine: executes one run end to end.

The AI Manager (LLM) decides *what* to do (the plan); this code decides *how*:
task ordering from the dependency DAG, parallelism, retries, budget, permissions,
approvals for running code, and the QA -> Code Reviewer -> QA fix loop.
Every step is persisted (tasks, artifacts, llm_usage, execution_events) and
pushed to WebSocket topics `runs:<id>` and `events`.
"""

import asyncio
import logging
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai_core.agents import prompts
from app.ai_core.agents.outputs import CodeChangeSet, Document, FileChange, Plan, ReviewResult, RunSummary
from app.ai_core.agents.runner import AgentCall, AgentProfile, QuotaExhaustedError, call_agent
from app.ai_core.execution.engine import CommandResult, run_command
from app.ai_core.execution.static_checks import scan_workspace
from app.ai_core.llm.provider import ModelFactory
from app.ai_core.orchestrator.plan import validate_plan
from app.ai_core.workspace.manager import WorkspaceAccessError, WorkspaceManager
from app.models import (
    Agent,
    Approval,
    Artifact,
    CommandExecution,
    ExecutionEvent,
    LlmUsage,
    Project,
    Task,
    TaskDependency,
    WorkflowRun,
)
from app.models.enums import ApprovalStatus, CommandStatus, RunStatus, TaskStatus
from app.realtime.hub import hub
from app.schemas.analytics import Limits, ModelPrice
from app.services.run import close_pending_approvals
from app.services.settings import SettingsService

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], AbstractContextManager[Session]]

MAX_FILES_PER_CHANGE = 40
MAX_FILE_BYTES = 200_000
MAX_CONTEXT_CHARS = 60_000
DOC_KINDS = ("requirements", "design")
REVIEW_KEY = "review"
RETEST_REVIEW_KEY = "retest_review"


class RunAborted(Exception):
    """Stops the run (budget exceeded, cancelled, approval rejected...)."""


class TaskError(Exception):
    """A task attempt failed; may be retried."""


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class RunContext:
    run_id: int
    project_id: int
    workspace_dir: str
    request_text: str
    budget_usd: Decimal | None
    limits: Limits
    pricing: dict[str, ModelPrice]
    agents: dict[str, AgentProfile]
    agent_ids: dict[str, int]
    permissions: dict[str, set[str]]
    fix_iterations: int = 0
    reviewed: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class WorkflowEngine:
    def __init__(
        self,
        session_factory: SessionFactory,
        workspaces: WorkspaceManager,
        model_factory: ModelFactory,
        approval_poll_seconds: float = 2.0,
        approval_timeout_seconds: float = 3600,
        llm_backoff: Sequence[float] | None = None,
    ):
        self.session_factory = session_factory
        self.workspaces = workspaces
        self.model_factory = model_factory
        self.approval_poll_seconds = approval_poll_seconds
        self.approval_timeout_seconds = approval_timeout_seconds
        self.llm_backoff = llm_backoff

    # ------------------------------------------------------------------ run

    async def run(self, run_id: int) -> None:
        ctx: RunContext | None = None
        try:
            ctx = self._load_context(run_id)
            await self._plan(ctx)
            await self._execute_dag(ctx)
            await self._finish(ctx)
        except RunAborted as exc:
            await self._fail_run(run_id, str(exc), cancelled=self._status(run_id) == RunStatus.CANCELLED)
        except Exception as exc:  # never leave a run stuck in "running"
            logger.exception("Run %s crashed", run_id)
            await self._fail_run(run_id, f"Lỗi hệ thống: {type(exc).__name__}: {exc}")

    def _load_context(self, run_id: int) -> RunContext:
        with self.session_factory() as db:
            run = db.get(WorkflowRun, run_id)
            project = db.get(Project, run.project_id)
            agents = list(db.scalars(select(Agent)))
            settings = SettingsService(db)
            limits = settings.limits()
            ctx = RunContext(
                run_id=run.id,
                project_id=project.id,
                workspace_dir=project.workspace_dir,
                request_text=run.request_text,
                budget_usd=run.budget_usd,
                limits=limits,
                pricing=settings.pricing(),
                agents={
                    a.code: AgentProfile(a.code, a.name, a.model, a.max_output_tokens, a.instructions)
                    for a in agents
                    if a.is_enabled
                },
                agent_ids={a.code: a.id for a in agents},
                permissions={a.code: {p.permission for p in a.permissions} for a in agents},
            )
            run.status = RunStatus.PLANNING
            run.started_at = _now()
            db.commit()
        if "manager" not in ctx.agents:
            raise RunAborted("AI Manager đang bị tắt")
        return ctx

    async def _plan(self, ctx: RunContext) -> None:
        await self._event(ctx, None, "run.planning", "AI Manager đang phân tích yêu cầu và lập kế hoạch")
        feedback = ""
        enabled = set(ctx.agents) - {"manager", "code_reviewer"}
        for attempt in range(1, ctx.limits.max_task_attempts + 1):
            call = await self._call(ctx, None, "manager", self._plan_prompt(ctx, feedback), Plan)
            errors = validate_plan(call.output, enabled)
            if not errors:
                break
            feedback = "Kế hoạch trước không hợp lệ:\n- " + "\n- ".join(errors)
            await self._event(ctx, None, "run.plan_invalid", f"Kế hoạch lần {attempt} không hợp lệ", {"errors": errors})
        else:
            raise RunAborted("AI Manager không lập được kế hoạch hợp lệ")

        plan = call.output
        with self.session_factory() as db:
            ids: dict[str, int] = {}
            for t in plan.tasks:
                task = Task(
                    run_id=ctx.run_id,
                    agent_id=ctx.agent_ids[t.agent_code],
                    task_key=t.key,
                    title=t.title[:300],
                    description=t.description,
                    max_attempts=ctx.limits.max_task_attempts,
                    input_data={"description": t.description},
                )
                db.add(task)
                db.flush()
                ids[t.key] = task.id
            for t in plan.tasks:
                for dep in t.depends_on:
                    db.add(TaskDependency(task_id=ids[t.key], depends_on_task_id=ids[dep]))
            db.add(Artifact(run_id=ctx.run_id, kind="plan", name="Kế hoạch của AI Manager",
                            content=plan.model_dump_json(indent=2)))
            db.get(WorkflowRun, ctx.run_id).status = RunStatus.RUNNING
            db.commit()
        await self._event(ctx, None, "run.planned", f"Đã lập kế hoạch {len(plan.tasks)} tác vụ: {plan.analysis[:500]}",
                          {"tasks": [t.model_dump() for t in plan.tasks]})

    def _plan_prompt(self, ctx: RunContext, feedback: str) -> str:
        enabled = ", ".join(sorted(set(ctx.agents) - {"manager", "code_reviewer"}))
        text = f"Yêu cầu của người dùng:\n{ctx.request_text}\n\nCác agent đang bật: {enabled}"
        return f"{text}\n\n{feedback}" if feedback else text

    # ------------------------------------------------------------------ DAG

    async def _execute_dag(self, ctx: RunContext) -> None:
        while True:
            self._raise_if_cancelled(ctx)
            tasks, deps = self._snapshot(ctx.run_id)
            status = {t.id: t.status for t in tasks}
            pending = [t for t in tasks if t.status == TaskStatus.PENDING]
            if not pending:
                break
            ready, blocked = [], []
            for t in pending:
                dep_status = [status[d] for d in deps.get(t.id, [])]
                if any(s in (TaskStatus.FAILED, TaskStatus.SKIPPED) for s in dep_status):
                    blocked.append(t)
                elif all(s == TaskStatus.COMPLETED for s in dep_status):
                    ready.append(t)
            for t in blocked:
                self._update_task(t.id, status=TaskStatus.SKIPPED, error="Tác vụ phụ thuộc bị lỗi")
                await self._event(ctx, t.id, "task.skipped", f"Bỏ qua '{t.title}' vì tác vụ phụ thuộc bị lỗi")
            if not ready:
                if blocked:
                    continue
                raise RunAborted("DAG bị kẹt: không còn tác vụ nào có thể chạy")
            # Independent tasks (e.g. backend_dev and frontend_dev) run in parallel;
            # a TaskGroup cancels the siblings if one aborts the run
            try:
                async with asyncio.TaskGroup() as group:
                    for t in ready:
                        group.create_task(self._execute_task(ctx, t.id))
            except* RunAborted as eg:
                raise eg.exceptions[0] from None

        failed = [t for t in self._snapshot(ctx.run_id)[0] if t.status == TaskStatus.FAILED]
        if failed:
            raise RunAborted(f"{len(failed)} tác vụ thất bại: " + ", ".join(t.title for t in failed))

    def _snapshot(self, run_id: int) -> tuple[list[Task], dict[int, list[int]]]:
        with self.session_factory() as db:
            tasks = list(db.scalars(select(Task).where(Task.run_id == run_id).order_by(Task.id)))
            deps: dict[int, list[int]] = {}
            for task_id, dep in db.execute(
                select(TaskDependency.task_id, TaskDependency.depends_on_task_id).join(Task, Task.id == TaskDependency.task_id)
                .where(Task.run_id == run_id)
            ):
                deps.setdefault(task_id, []).append(dep)
            return tasks, deps

    async def _execute_task(self, ctx: RunContext, task_id: int) -> None:
        with self.session_factory() as db:
            task = db.get(Task, task_id)
            code = db.scalar(select(Agent.code).where(Agent.id == task.agent_id))
            title, max_attempts, key = task.title, task.max_attempts, task.task_key
            description = task.description or ""

        last_error = ""
        for attempt in range(1, max_attempts + 1):
            self._raise_if_cancelled(ctx)
            self._check_budget(ctx)
            self._update_task(task_id, status=TaskStatus.RUNNING, attempt=attempt, started_at=_now(), error=None)
            await self._event(ctx, task_id, "task.started", f"{code} bắt đầu: {title} (lần {attempt})")
            # Tell the agent why its previous attempt was rejected so it can correct itself
            instructions = description + (
                f"\n\nLần thử trước bị hệ thống từ chối vì: {last_error}\nHãy khắc phục lỗi này." if last_error else ""
            )
            try:
                output = await self._dispatch(ctx, task_id, code, key, instructions)
            except (RunAborted, asyncio.CancelledError):
                raise
            except Exception as exc:  # LLM/validation/permission error -> retry
                message = f"{type(exc).__name__}: {exc}"[:2000]
                last_error = message
                self._update_task(task_id, status=TaskStatus.FAILED if attempt == max_attempts else TaskStatus.RUNNING,
                                  error=message, finished_at=_now() if attempt == max_attempts else None)
                await self._event(ctx, task_id, "task.failed" if attempt == max_attempts else "task.retry",
                                  f"{title}: {message}")
                continue
            self._update_task(task_id, status=TaskStatus.COMPLETED, output_data=output, finished_at=_now())
            await self._event(ctx, task_id, "task.completed", f"{code} hoàn thành: {title}", output)
            return

    async def _dispatch(self, ctx: RunContext, task_id: int, code: str, key: str, description: str) -> dict[str, Any]:
        if code in ("business_analyst", "architect"):
            return await self._document_task(ctx, task_id, code, description)
        if code in ("backend_dev", "frontend_dev"):
            return await self._code_task(ctx, task_id, code, description)
        if code == "qa_tester":
            if key.startswith("retest"):
                return await self._test_cycle(ctx, task_id)
            return await self._qa_task(ctx, task_id, description)
        if code == "code_reviewer":
            if key == REVIEW_KEY:
                # description carries only the previous attempt's feedback (review tasks have none)
                return await self._quality_review(ctx, task_id, description.strip())
            return await self._review_task(ctx, task_id)
        raise TaskError(f"Không có trình xử lý cho agent {code}")

    # ------------------------------------------------------------------ agent tasks

    async def _document_task(self, ctx: RunContext, task_id: int, code: str, description: str) -> dict[str, Any]:
        prompt = self._compose(ctx, description, docs=True)
        call = await self._call(ctx, task_id, code, prompt, Document)
        doc = call.output
        name = PurePosixPath(doc.filename).name or ("SRS.md" if code == "business_analyst" else "DESIGN.md")
        if not name.lower().endswith(".md"):
            name += ".md"
        path = f"docs/{name}"
        await self._write_files(ctx, task_id, code, [FileChange(path=path, content=doc.content)])
        kind = "requirements" if code == "business_analyst" else "design"
        self._add_artifact(ctx, task_id, kind, name, content=doc.content, file_path=path)
        return {"file": path, "summary": doc.summary}

    async def _code_task(self, ctx: RunContext, task_id: int, code: str, description: str) -> dict[str, Any]:
        # The agent must see the current code of its own area, or an iteration request
        # ("keep existing features") gets a from-scratch rewrite (seen in run #8)
        area = "backend" if code == "backend_dev" else "frontend"
        prompt = self._compose(ctx, description, docs=True, sources=(area,))
        call = await self._call(ctx, task_id, code, prompt, CodeChangeSet)
        written = await self._write_files(ctx, task_id, code, call.output.files)
        for path in written:
            self._add_artifact(ctx, task_id, "source_file", PurePosixPath(path).name, file_path=path)
        return {"files": written, "summary": call.output.summary}

    async def _qa_task(self, ctx: RunContext, task_id: int, description: str) -> dict[str, Any]:
        prompt = self._compose(ctx, description, docs=True, sources=("backend",))
        call = await self._call(ctx, task_id, "qa_tester", prompt, CodeChangeSet)
        written = await self._write_files(ctx, task_id, "qa_tester", call.output.files)
        for path in written:
            self._add_artifact(ctx, task_id, "test_file", PurePosixPath(path).name, file_path=path)
        result = await self._test_cycle(ctx, task_id)
        return {**result, "files": written, "summary": call.output.summary}

    async def _review_task(self, ctx: RunContext, task_id: int) -> dict[str, Any]:
        with self.session_factory() as db:
            report = db.scalar(
                select(Artifact.content).where(Artifact.run_id == ctx.run_id, Artifact.kind == "test_report")
                .order_by(Artifact.id.desc())
            )
        prompt = self._compose(
            ctx, f"Kết quả pytest đang lỗi:\n```\n{report}\n```\nHãy sửa để toàn bộ test đúng với SRS/DESIGN đều qua.",
            docs=True, sources=("backend", "tests"),
        )
        call = await self._call(ctx, task_id, "code_reviewer", prompt, ReviewResult)
        review = call.output
        written = await self._write_files(ctx, task_id, "code_reviewer", review.files)
        self._add_artifact(ctx, task_id, "review", "Kết quả review",
                           content=f"## Nguyên nhân\n{review.root_cause}\n\n## Vấn đề\n" +
                           "\n".join(f"- {i}" for i in review.issues) + f"\n\n## Đã sửa\n{review.summary}")
        return {"files": written, "root_cause": review.root_cause, "issues": review.issues}

    async def _quality_review(self, ctx: RunContext, task_id: int, description: str) -> dict[str, Any]:
        """Mandatory review once tests pass: security, correctness vs SRS, error handling.

        A deterministic scan (static_checks) runs before and after the LLM review; findings
        the reviewer leaves unfixed make the attempt fail (retried with feedback), and on the
        last attempt they are reported as unresolved instead of being silently accepted.
        """
        root = self.workspaces.project_root(ctx.workspace_dir)
        before = await asyncio.to_thread(scan_workspace, root)
        if before:
            await self._event(ctx, task_id, "security.findings", f"Quét tĩnh phát hiện {len(before)} vấn đề bảo mật",
                              {"findings": [f.to_dict() for f in before]})
        task_note = "Toàn bộ test hiện đang đạt. Hãy rà soát mã nguồn backend, frontend và test theo checklist."
        if before:
            task_note += ("\n\nQUÉT TĨNH TỰ ĐỘNG phát hiện các lỗi sau, BẮT BUỘC phải sửa (trả về file đã sửa):\n"
                          + "\n".join(f.describe() for f in before))
        if description:  # feedback from a previous attempt
            task_note += f"\n\n{description}"
        prompt = self._compose(ctx, task_note, docs=True, sources=("backend", "frontend", "tests"))
        call = await self._call(ctx, task_id, "code_reviewer", prompt, ReviewResult,
                                instructions=prompts.QUALITY_REVIEW)
        review = call.output
        written = await self._write_files(ctx, task_id, "code_reviewer", review.files)
        after = await asyncio.to_thread(scan_workspace, root)

        with self.session_factory() as db:
            task = db.get(Task, task_id)
            last_attempt = task.attempt >= task.max_attempts
        if after and not last_attempt:
            if written:  # keep partial fixes, but they still need QA
                self._add_retest_after_review(ctx, task_id)
            raise TaskError("Quét tĩnh vẫn còn lỗi bảo mật chưa sửa:\n" + "\n".join(f.describe() for f in after))

        self._add_artifact(ctx, task_id, "review", "Code review bắt buộc",
                           content="## Đánh giá\n" + review.root_cause + "\n\n## Vấn đề\n" +
                           ("\n".join(f"- {i}" for i in review.issues) or "- Không phát hiện vấn đề") +
                           "\n\n## Quét tĩnh\n" +
                           (f"- Trước review: {len(before)} · sau review: {len(after)}" +
                            "".join(f"\n- CHƯA XỬ LÝ: {f.describe()}" for f in after)) +
                           f"\n\n## Thay đổi\n{review.summary}")
        if after:
            await self._event(ctx, task_id, "security.unresolved",
                              f"Còn {len(after)} lỗi bảo mật chưa được Code Reviewer xử lý",
                              {"findings": [f.to_dict() for f in after]})
        if written:
            self._add_retest_after_review(ctx, task_id)
            await self._event(ctx, task_id, "review.changed", f"Code Reviewer sửa {len(written)} file, chuyển QA kiểm thử lại",
                              {"files": written, "issues": review.issues})
        return {"files": written, "issues": review.issues, "summary": review.summary,
                "security_findings_before": len(before), "security_unresolved": [f.describe() for f in after]}

    def _add_retest_after_review(self, ctx: RunContext, review_task_id: int) -> None:
        """Any change made by the reviewer must be re-verified by QA (added once per run)."""
        with self.session_factory() as db:
            exists = db.scalar(select(Task.id).where(Task.run_id == ctx.run_id, Task.task_key == RETEST_REVIEW_KEY))
        if not exists:
            self._add_tasks(ctx, [("qa_tester", RETEST_REVIEW_KEY, "Kiểm thử lại sau code review", 1, review_task_id)])

    async def _test_cycle(self, ctx: RunContext, task_id: int) -> dict[str, Any]:
        result = await self._run_tests(ctx, task_id)
        report = f"exit_code={result.exit_code}\n{result.stdout}\n{result.stderr}".strip()
        self._add_artifact(ctx, task_id, "test_report", "Kết quả pytest", content=report)
        if result.succeeded:
            async with ctx.lock:
                schedule_review = (ctx.limits.mandatory_review and not ctx.reviewed and "code_reviewer" in ctx.agents)
                ctx.reviewed = ctx.reviewed or schedule_review
            if schedule_review:
                self._add_tasks(ctx, [("code_reviewer", REVIEW_KEY, "Code review bảo mật & chất lượng",
                                       ctx.limits.max_task_attempts, task_id)])
                await self._event(ctx, task_id, "review.scheduled", "Test đạt, chuyển Code Reviewer rà soát bắt buộc")
            return {"tests_passed": True, "exit_code": result.exit_code}

        async with ctx.lock:
            if ctx.fix_iterations >= ctx.limits.max_fix_iterations:
                raise RunAborted(f"Test vẫn lỗi sau {ctx.fix_iterations} vòng sửa")
            ctx.fix_iterations += 1
            n = ctx.fix_iterations
        # Grow the DAG: Code Reviewer fixes, then QA re-tests
        fix_id = self._add_tasks(ctx, [("code_reviewer", f"fix_{n}", f"Phân tích & sửa lỗi test (vòng {n})",
                                        ctx.limits.max_task_attempts, task_id)])[0]
        self._add_tasks(ctx, [("qa_tester", f"retest_{n}", f"Kiểm thử lại (vòng {n})", 1, fix_id)])
        await self._event(ctx, task_id, "qa.failed", f"Test lỗi, chuyển cho Code Reviewer (vòng {n})",
                          {"exit_code": result.exit_code})
        # The QA task itself is done (it produced a report); the fix loop continues in new tasks
        return {"tests_passed": False, "exit_code": result.exit_code, "fix_iteration": n}

    async def _run_tests(self, ctx: RunContext, task_id: int) -> CommandResult:
        approval_id = None
        if ctx.limits.require_command_approval:
            approval_id = await self._await_approval(ctx, task_id)
        workspace = self.workspaces.project_root(ctx.workspace_dir)
        await self._event(ctx, task_id, "command.started", "Chạy pytest trong workspace")
        result = await asyncio.to_thread(run_command, "pytest", workspace, ctx.limits.command_timeout_seconds)
        with self.session_factory() as db:
            db.add(CommandExecution(
                run_id=ctx.run_id, task_id=task_id, approval_id=approval_id, command=result.command, args=result.args,
                cwd=ctx.workspace_dir, exit_code=result.exit_code, stdout=result.stdout, stderr=result.stderr,
                duration_ms=result.duration_ms, finished_at=_now(),
                status=CommandStatus.TIMED_OUT if result.timed_out
                else CommandStatus.SUCCEEDED if result.succeeded else CommandStatus.FAILED,
            ))
            db.commit()
        await self._event(ctx, task_id, "command.finished",
                          f"pytest {'đạt' if result.succeeded else 'lỗi'} (exit {result.exit_code}, {result.duration_ms} ms)",
                          {"stdout_tail": result.stdout[-1500:]})
        return result

    async def _await_approval(self, ctx: RunContext, task_id: int) -> int:
        workspace = self.workspaces.project_root(ctx.workspace_dir)
        with self.session_factory() as db:
            approval = Approval(
                run_id=ctx.run_id, task_id=task_id, kind="command",
                title="Chạy bộ test (pytest) do AI sinh ra trên máy này",
                payload={"command": "pytest", "cwd": f"workspaces/{workspace.name}",
                         "note": "Code do agent viết sẽ được thực thi với quyền của tài khoản đang chạy backend."},
            )
            db.add(approval)
            db.get(Task, task_id).status = TaskStatus.WAITING_APPROVAL
            db.get(WorkflowRun, ctx.run_id).status = RunStatus.WAITING_APPROVAL
            db.commit()
            approval_id = approval.id
        await self._event(ctx, task_id, "approval.requested", "Chờ phê duyệt chạy pytest", {"approval_id": approval_id})
        await hub.publish("approvals", "approval.created", {"id": approval_id, "run_id": ctx.run_id})

        waited = 0.0
        while waited < self.approval_timeout_seconds:
            await asyncio.sleep(self.approval_poll_seconds)
            waited += self.approval_poll_seconds
            with self.session_factory() as db:
                status = db.scalar(select(Approval.status).where(Approval.id == approval_id))
                run_status = db.scalar(select(WorkflowRun.status).where(WorkflowRun.id == ctx.run_id))
            if run_status == RunStatus.CANCELLED:
                raise RunAborted("Run đã bị hủy")
            if status == ApprovalStatus.APPROVED:
                self._update_task(task_id, status=TaskStatus.RUNNING)
                self._set_run_status(ctx.run_id, RunStatus.RUNNING)
                return approval_id
            if status == ApprovalStatus.REJECTED:
                raise RunAborted("Người dùng từ chối chạy test")
        raise RunAborted("Hết thời gian chờ phê duyệt")

    # ------------------------------------------------------------------ finish

    async def _finish(self, ctx: RunContext) -> None:
        with self.session_factory() as db:
            tasks = list(db.scalars(select(Task).where(Task.run_id == ctx.run_id).order_by(Task.id)))
            outline = "\n".join(f"- [{t.status.value}] {t.title}: {t.output_data}" for t in tasks)
        prompt = f"Yêu cầu:\n{ctx.request_text}\n\nKết quả các tác vụ:\n{outline}"[:MAX_CONTEXT_CHARS]
        summary = await self._call(ctx, None, "manager", prompt, RunSummary, instructions=prompts.SUMMARIZER)
        with self.session_factory() as db:
            run = db.get(WorkflowRun, ctx.run_id)
            run.summary = summary.output.summary
            run.status = RunStatus.COMPLETED
            run.finished_at = _now()
            db.commit()
        await self._event(ctx, None, "run.completed", "AI Manager đã tổng hợp kết quả")

    async def _fail_run(self, run_id: int, reason: str, cancelled: bool = False) -> None:
        with self.session_factory() as db:
            run = db.get(WorkflowRun, run_id)
            if run is None:
                return
            run.status = RunStatus.CANCELLED if cancelled else RunStatus.FAILED
            run.error = reason[:4000]
            run.finished_at = _now()
            for task in db.scalars(select(Task).where(
                Task.run_id == run_id, Task.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL])
            )):
                task.status = TaskStatus.SKIPPED
            close_pending_approvals(db, run_id, f"Run kết thúc: {reason}"[:2000])
            db.commit()
            project_id = run.project_id
        await self._emit(run_id, project_id, None, "run.cancelled" if cancelled else "run.failed", reason, None)

    # ------------------------------------------------------------------ helpers

    async def _call(self, ctx: RunContext, task_id: int | None, code: str, prompt: str,
                    output_type: type[BaseModel], instructions: str | None = None) -> AgentCall:
        profile = ctx.agents.get(code)
        if profile is None:
            raise RunAborted(f"Agent {code} đang bị tắt")
        async def on_retry(exc: Exception, delay: float, n: int) -> None:
            self._raise_if_cancelled(ctx)
            await self._event(ctx, task_id, "llm.retry",
                              f"{code}: nhà cung cấp LLM báo {type(exc).__name__}, chờ {delay:g}s rồi gọi lại (lần {n})")

        try:
            call = await call_agent(profile, prompt, output_type, self.model_factory, instructions,
                                    on_retry=on_retry, backoff=self.llm_backoff)
        except QuotaExhaustedError as exc:
            # Retrying the task cannot succeed today: stop the run with an actionable message
            raise RunAborted(f"{profile.name}: {exc}") from exc
        price = ctx.pricing.get(call.model)
        cost = Decimal("0")
        if price:
            uncached = max(call.input_tokens - call.cached_input_tokens, 0)
            cost = Decimal(str(
                (uncached * price.input_per_1m + call.cached_input_tokens * price.cached_input_per_1m
                 + call.output_tokens * price.output_per_1m) / 1_000_000
            )).quantize(Decimal("0.000001"))
        with self.session_factory() as db:
            db.add(LlmUsage(
                run_id=ctx.run_id, task_id=task_id, agent_id=ctx.agent_ids[code], model=call.model,
                input_tokens=call.input_tokens, cached_input_tokens=call.cached_input_tokens,
                output_tokens=call.output_tokens, request_count=call.requests, cost_usd=cost,
                latency_ms=call.latency_ms,
            ))
            run = db.get(WorkflowRun, ctx.run_id)
            run.total_input_tokens += call.input_tokens
            run.total_output_tokens += call.output_tokens
            run.total_cost_usd += cost
            db.commit()
        return call

    def _raise_if_cancelled(self, ctx: RunContext) -> None:
        if self._status(ctx.run_id) == RunStatus.CANCELLED:
            raise RunAborted("Run đã bị hủy")

    def _check_budget(self, ctx: RunContext) -> None:
        budget = ctx.budget_usd
        if budget is None:
            return
        with self.session_factory() as db:
            spent = db.scalar(select(func.coalesce(func.sum(LlmUsage.cost_usd), 0)).where(LlmUsage.run_id == ctx.run_id))
        if Decimal(spent) >= budget:
            raise RunAborted(f"Vượt ngân sách run: đã dùng ${spent} / ${budget}")

    def _compose(self, ctx: RunContext, description: str, docs: bool = False, sources: tuple[str, ...] = ()) -> str:
        parts = [f"Yêu cầu gốc của người dùng:\n{ctx.request_text}", f"Nhiệm vụ của bạn:\n{description}"]
        if docs:
            with self.session_factory() as db:
                for name, content in db.execute(
                    select(Artifact.name, Artifact.content)
                    .where(Artifact.run_id == ctx.run_id, Artifact.kind.in_(DOC_KINDS)).order_by(Artifact.id)
                ):
                    parts.append(f"=== {name} ===\n{content}")
        root = self.workspaces.project_root(ctx.workspace_dir)
        if docs:
            existing = sorted(
                p.relative_to(root).as_posix() for p in root.rglob("*")
                if p.is_file() and not ({"__pycache__", ".pytest_cache"} & set(p.parts))
            )
            parts.append("Danh sách file hiện có trong workspace:\n" + ("\n".join(f"- {f}" for f in existing) or "(trống)"))
        for area in sources:
            base = root / area
            if not base.is_dir():
                continue
            for path in sorted(p for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
                parts.append(f"=== {path.relative_to(root).as_posix()} ===\n{path.read_text('utf-8', errors='replace')}")
        text = "\n\n".join(parts)
        return text if len(text) <= MAX_CONTEXT_CHARS else text[:MAX_CONTEXT_CHARS] + "\n…[ngữ cảnh đã cắt bớt]"

    async def _write_files(self, ctx: RunContext, task_id: int | None, code: str, files: list[FileChange]) -> list[str]:
        """Write agent output into the workspace, enforcing per-agent write areas.

        Files outside the agent's areas are dropped (models often "helpfully" emit
        docs/tests too) and reported; a path escaping the workspace rejects the
        whole change set. Nothing is written until every path is validated.
        """
        if len(files) > MAX_FILES_PER_CHANGE:
            raise TaskError(f"Quá nhiều file ({len(files)} > {MAX_FILES_PER_CHANGE})")
        allowed = {p.split(":", 1)[1] for p in ctx.permissions.get(code, set()) if p.startswith("fs.write:")}
        planned: list[tuple[str, Any, FileChange]] = []
        rejected: list[str] = []
        for change in files:
            rel = change.path.strip().replace("\\", "/").removeprefix("./")
            path = self.workspaces.resolve(ctx.workspace_dir, rel)  # raises on escape attempts
            if rel.split("/", 1)[0] not in allowed:
                rejected.append(rel)
                continue
            if len(change.content.encode("utf-8")) > MAX_FILE_BYTES:
                raise TaskError(f"File quá lớn: {rel}")
            if change.delete and path.is_dir():
                raise TaskError(f"Chỉ được xóa file, không xóa thư mục: {rel}")
            planned.append((rel, path, change))
        if rejected:
            await self._event(ctx, task_id, "files.rejected",
                              f"{code} không có quyền ghi {len(rejected)} file (chỉ được ghi {sorted(allowed)}); đã bỏ qua",
                              {"files": rejected})
        if not planned and files:
            raise WorkspaceAccessError(
                f"{code} không có quyền ghi {', '.join(repr(r) for r in rejected)} (được ghi: {sorted(allowed)})")
        written, deleted = [], []
        for rel, path, change in planned:
            if change.delete:
                if path.is_file():
                    path.unlink()
                    deleted.append(rel)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(change.content, encoding="utf-8")
            written.append(rel)
        if deleted:
            await self._event(ctx, task_id, "files.deleted", f"{code} xóa {len(deleted)} file lỗi thời", {"files": deleted})
        return written

    def _add_tasks(self, ctx: RunContext, specs: list[tuple[str, str, str, int, int]]) -> list[int]:
        """Append tasks to the running DAG: (agent_code, key, title, max_attempts, depends_on_task_id)."""
        with self.session_factory() as db:
            tasks = [Task(run_id=ctx.run_id, agent_id=ctx.agent_ids[code], task_key=key, title=title,
                          max_attempts=attempts) for code, key, title, attempts, _ in specs]
            db.add_all(tasks)
            db.flush()
            db.add_all([TaskDependency(task_id=t.id, depends_on_task_id=spec[4]) for t, spec in zip(tasks, specs)])
            db.commit()
            return [t.id for t in tasks]

    def _add_artifact(self, ctx: RunContext, task_id: int, kind: str, name: str,
                      content: str | None = None, file_path: str | None = None) -> None:
        with self.session_factory() as db:
            db.add(Artifact(run_id=ctx.run_id, task_id=task_id, kind=kind, name=name[:300],
                            content=content, file_path=file_path))
            db.commit()

    def _update_task(self, task_id: int, **fields: Any) -> None:
        with self.session_factory() as db:
            task = db.get(Task, task_id)
            for k, v in fields.items():
                setattr(task, k, v)
            db.commit()

    def _set_run_status(self, run_id: int, status: RunStatus) -> None:
        with self.session_factory() as db:
            db.get(WorkflowRun, run_id).status = status
            db.commit()

    def _status(self, run_id: int) -> RunStatus | None:
        with self.session_factory() as db:
            return db.scalar(select(WorkflowRun.status).where(WorkflowRun.id == run_id))

    async def _event(self, ctx: RunContext, task_id: int | None, event_type: str, message: str,
                     data: dict[str, Any] | None = None) -> None:
        await self._emit(ctx.run_id, ctx.project_id, task_id, event_type, message, data)

    async def _emit(self, run_id: int, project_id: int, task_id: int | None, event_type: str, message: str,
                    data: dict[str, Any] | None) -> None:
        with self.session_factory() as db:
            event = ExecutionEvent(run_id=run_id, task_id=task_id, event_type=event_type, message=message[:4000], data=data)
            db.add(event)
            db.commit()
            payload = {"id": event.id, "run_id": run_id, "project_id": project_id, "task_id": task_id,
                       "event_type": event_type, "message": event.message}
        await hub.publish(f"runs:{run_id}", event_type, payload)
        await hub.publish("events", event_type, payload)
