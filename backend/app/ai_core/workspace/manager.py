"""Workspace isolation: every project gets its own folder and agents can never
read or write outside of it."""

import re
import unicodedata
import uuid
from pathlib import Path

from app.core.exceptions import AppError


class WorkspaceAccessError(AppError):
    status_code = 403
    code = "workspace_access_denied"


def make_workspace_dir_name(project_name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", project_name.replace("đ", "d").replace("Đ", "D"))
    ascii_name = ascii_name.encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:40] or "project"
    return f"{slug}-{uuid.uuid4().hex[:8]}"


class WorkspaceManager:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def project_root(self, workspace_dir: str) -> Path:
        path = (self.root / workspace_dir).resolve()
        if path.parent != self.root:
            raise WorkspaceAccessError(f"Invalid workspace directory: {workspace_dir!r}")
        return path

    def create(self, workspace_dir: str) -> Path:
        path = self.project_root(workspace_dir)
        path.mkdir(parents=True, exist_ok=False)
        return path

    def resolve(self, workspace_dir: str, relative_path: str) -> Path:
        """Resolve a path requested by an agent; reject anything escaping the workspace."""
        base = self.project_root(workspace_dir)
        candidate = Path(relative_path)
        if candidate.is_absolute() or candidate.drive:
            raise WorkspaceAccessError("Absolute paths are not allowed")
        resolved = (base / candidate).resolve()
        if not resolved.is_relative_to(base):
            raise WorkspaceAccessError(f"Path escapes the workspace: {relative_path!r}")
        return resolved
