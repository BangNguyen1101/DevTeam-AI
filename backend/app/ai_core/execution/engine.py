"""Execution Engine: runs only pre-defined commands inside a project workspace.

No shell, no arbitrary commands: callers pick a command *name* from ALLOWED_COMMANDS.
The child process gets a minimal environment (no API keys / DB credentials), a hard
timeout and truncated output.
"""

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.exceptions import AppError

MAX_OUTPUT_CHARS = 20_000

# name -> argv builder. sys.executable is the backend's own venv interpreter.
ALLOWED_COMMANDS: dict[str, list[str]] = {
    "pytest": [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--no-header", "-rf", "tests"],
}

_PASSTHROUGH_ENV = ("SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "PATHEXT", "COMSPEC")


class CommandNotAllowedError(AppError):
    status_code = 403
    code = "command_not_allowed"


@dataclass
class CommandResult:
    command: str
    args: list[str]
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[: MAX_OUTPUT_CHARS // 2] + "\n…[đã cắt bớt]…\n" + text[-MAX_OUTPUT_CHARS // 2 :]


def build_env(workspace: Path) -> dict[str, str]:
    env = {k: os.environ[k] for k in _PASSTHROUGH_ENV if k in os.environ}
    env.update(
        PYTHONPATH=str(workspace / "backend"),
        PYTHONIOENCODING="utf-8",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONNOUSERSITE="1",
    )
    return env


def run_command(name: str, workspace: Path, timeout_seconds: int) -> CommandResult:
    if name not in ALLOWED_COMMANDS:
        raise CommandNotAllowedError(f"Lệnh '{name}' không nằm trong allowlist")
    argv = ALLOWED_COMMANDS[name]
    started = time.perf_counter()
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, shell=False
            argv,
            cwd=workspace,
            env=build_env(workspace),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            shell=False,
            stdin=subprocess.DEVNULL,
        )
        exit_code, stdout, stderr, timed_out = proc.returncode, proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired as exc:
        exit_code, timed_out = None, True
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = f"Quá thời gian {timeout_seconds}s"
    return CommandResult(
        command=name,
        args=argv[1:],
        exit_code=exit_code,
        stdout=_truncate(stdout),
        stderr=_truncate(stderr),
        duration_ms=int((time.perf_counter() - started) * 1000),
        timed_out=timed_out,
    )
