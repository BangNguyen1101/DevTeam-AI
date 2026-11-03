"""Read-only browsing of a project's workspace (files written by agents)."""

from pathlib import Path

from pydantic import BaseModel

from app.ai_core.workspace.manager import WorkspaceAccessError, WorkspaceManager
from app.core.exceptions import AppError, NotFoundError

MAX_ENTRIES = 2000
MAX_PREVIEW_BYTES = 200_000
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", ".pytest_cache"}


class FileEntry(BaseModel):
    path: str
    is_dir: bool
    size: int | None


class FileContent(BaseModel):
    path: str
    size: int
    content: str
    truncated: bool


class UnreadableFileError(AppError):
    status_code = 415
    code = "unsupported_file"


def list_files(workspaces: WorkspaceManager, workspace_dir: str) -> list[FileEntry]:
    root = workspaces.project_root(workspace_dir)
    if not root.is_dir():
        return []
    entries: list[FileEntry] = []

    def walk(directory: Path) -> None:
        for child in sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if len(entries) >= MAX_ENTRIES:
                return
            if child.is_symlink():  # never follow links out of the workspace
                continue
            rel = child.relative_to(root).as_posix()
            if child.is_dir():
                entries.append(FileEntry(path=rel, is_dir=True, size=None))
                if child.name not in SKIP_DIRS:
                    walk(child)
            else:
                entries.append(FileEntry(path=rel, is_dir=False, size=child.stat().st_size))

    walk(root)
    return entries


def read_file(workspaces: WorkspaceManager, workspace_dir: str, relative_path: str) -> FileContent:
    path = workspaces.resolve(workspace_dir, relative_path)
    if path.is_symlink():
        raise WorkspaceAccessError("Symbolic links are not readable")
    if not path.is_file():
        raise NotFoundError(f"File not found: {relative_path}")
    size = path.stat().st_size
    with path.open("rb") as f:
        raw = f.read(MAX_PREVIEW_BYTES)
    if b"\x00" in raw:
        raise UnreadableFileError("Binary files cannot be previewed")
    return FileContent(
        path=relative_path,
        size=size,
        content=raw.decode("utf-8", errors="replace"),
        truncated=size > MAX_PREVIEW_BYTES,
    )
