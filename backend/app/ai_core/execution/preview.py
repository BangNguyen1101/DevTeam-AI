"""Live preview of the app a team of agents generated.

The generated FastAPI backend is started on demand (an explicit user click) as a
subprocess on 127.0.0.1 with the same minimal, secret-free environment as test
runs, and stopped after PREVIEW_IDLE_SECONDS without traffic. The browser reaches
it only through /preview/{token}/..., which serves frontend/ files and proxies
/preview/{token}/api/* to the subprocess. Pages are sandboxed (opaque origin), so
AI-written JavaScript can't use the DevTeam session cookie.
"""

import asyncio
import logging
import secrets
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.ai_core.execution.engine import build_env
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

PREVIEW_IDLE_SECONDS = 15 * 60
MAX_PREVIEWS = 2
START_TIMEOUT_SECONDS = 20
LOG_TAIL_CHARS = 4000


class PreviewError(AppError):
    status_code = 409
    code = "preview_error"


@dataclass
class Preview:
    project_id: int
    token: str
    root: Path
    port: int | None
    process: subprocess.Popen | None
    started_at: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)
    log_path: Path | None = None

    @property
    def api_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def log_tail(self) -> str:
        if not self.log_path or not self.log_path.exists():
            return ""
        return self.log_path.read_text("utf-8", errors="replace")[-LOG_TAIL_CHARS:]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


class PreviewManager:
    def __init__(self, idle_seconds: float = PREVIEW_IDLE_SECONDS, max_previews: int = MAX_PREVIEWS):
        self.idle_seconds = idle_seconds
        self.max_previews = max_previews
        self._by_project: dict[int, Preview] = {}
        self._lock = threading.Lock()

    # -- lifecycle -------------------------------------------------------------

    def start(self, project_id: int, root: Path) -> Preview:
        """Start (or return) the preview of a project workspace. Blocking; call in a thread."""
        self.reap_idle()
        with self._lock:
            current = self._by_project.get(project_id)
            if current and (current.process is None or current.api_running):
                current.last_access = time.time()
                return current
            if current:  # backend crashed: restart
                self._stop_locked(project_id)
            if len(self._by_project) >= self.max_previews:
                raise PreviewError(f"Đang có {self.max_previews} bản xem trước chạy; hãy dừng bớt một bản")
            if not (root / "frontend" / "index.html").is_file():
                raise PreviewError("Workspace chưa có frontend/index.html để xem trước")

            port = process = log_path = None
            if (root / "backend" / "app" / "main.py").is_file():
                port = _free_port()
                log_path = root.parent / f".preview-{root.name}.log"
                log = log_path.open("w", encoding="utf-8")
                process = subprocess.Popen(  # noqa: S603 - fixed argv, shell=False
                    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port),
                     "--no-access-log"],
                    cwd=root, env=build_env(root), stdout=log, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL, shell=False,
                )
                log.close()
            preview = Preview(project_id, secrets.token_urlsafe(24), root, port, process, log_path=log_path)
            self._by_project[project_id] = preview

        if process is not None:
            deadline = time.time() + START_TIMEOUT_SECONDS
            while time.time() < deadline and process.poll() is None and not _port_open(port):
                time.sleep(0.2)
            if not (process.poll() is None and _port_open(port)):
                tail = preview.log_tail()
                self.stop(project_id)
                raise PreviewError(f"Backend của ứng dụng không khởi động được:\n{tail[-1500:]}")
        logger.info("Preview started for project %s (api port %s)", project_id, port)
        return preview

    def stop(self, project_id: int) -> bool:
        with self._lock:
            return self._stop_locked(project_id)

    def _stop_locked(self, project_id: int) -> bool:
        preview = self._by_project.pop(project_id, None)
        if preview is None:
            return False
        if preview.process is not None and preview.process.poll() is None:
            preview.process.terminate()
            try:
                preview.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                preview.process.kill()
        logger.info("Preview stopped for project %s", project_id)
        return True

    def stop_all(self) -> None:
        with self._lock:
            for project_id in list(self._by_project):
                self._stop_locked(project_id)

    def reap_idle(self) -> None:
        now = time.time()
        with self._lock:
            for project_id, p in list(self._by_project.items()):
                if now - p.last_access > self.idle_seconds:
                    self._stop_locked(project_id)

    # -- lookup ----------------------------------------------------------------

    def get(self, project_id: int) -> Preview | None:
        return self._by_project.get(project_id)

    def by_token(self, token: str) -> Preview | None:
        for p in list(self._by_project.values()):
            if secrets.compare_digest(p.token, token):
                if time.time() - p.last_access > self.idle_seconds:
                    self.stop(p.project_id)
                    return None
                p.last_access = time.time()
                return p
        return None


previews = PreviewManager()


async def reaper(interval: float = 60) -> None:
    """Background task: stop idle previews."""
    while True:
        await asyncio.sleep(interval)
        await asyncio.to_thread(previews.reap_idle)
