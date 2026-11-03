import pytest

from app.ai_core.workspace.manager import WorkspaceAccessError, WorkspaceManager, make_workspace_dir_name


@pytest.fixture
def manager(tmp_path):
    m = WorkspaceManager(tmp_path)
    m.create("demo-1234abcd")
    return m


def test_dir_name_is_ascii_slug():
    name = make_workspace_dir_name("Đặt lịch khám bệnh!")
    assert name.startswith("dat-lich-kham-benh-")
    assert name.isascii()


def test_resolve_inside_workspace(manager, tmp_path):
    assert manager.resolve("demo-1234abcd", "backend/app/main.py") == tmp_path / "demo-1234abcd" / "backend/app/main.py"


@pytest.mark.parametrize(
    "path",
    ["../other/secret.txt", "backend/../../escape.txt", "C:\\Windows\\system.ini", "/etc/passwd", "\\\\server\\share"],
)
def test_resolve_rejects_escape(manager, path):
    with pytest.raises(WorkspaceAccessError):
        manager.resolve("demo-1234abcd", path)


@pytest.mark.parametrize("workspace_dir", ["..", "../x", "a/b", ""])
def test_invalid_workspace_dir(manager, workspace_dir):
    with pytest.raises(WorkspaceAccessError):
        manager.project_root(workspace_dir)
