"""seed agents and default settings

Revision ID: a060f447a1ae
Revises: 1f87fbd3a806
Create Date: 2026-11-03

Seeds the AI Manager + 6 specialist agents with their permissions and the
runtime limits. Models are defaults only; they are editable in Settings.
"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a060f447a1ae"
down_revision: Union[str, None] = "1f87fbd3a806"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_MODEL = "gpt-5-mini"
STRONG_MODEL = "gpt-5"

# code, name, role, model, max_output_tokens, permissions
AGENTS = [
    ("manager", "AI Manager", "Phân tích yêu cầu, lập kế hoạch, phân công và tổng hợp kết quả.",
     STRONG_MODEL, 8000, ["plan.create", "task.assign", "fs.read"]),
    ("business_analyst", "Business Analyst", "Phân tích nghiệp vụ, user stories, acceptance criteria, SRS.",
     DEFAULT_MODEL, 8000, ["fs.read", "fs.write:docs"]),
    ("architect", "Software Architect", "Thiết kế kiến trúc, database, API và tài liệu kỹ thuật.",
     STRONG_MODEL, 12000, ["fs.read", "fs.write:docs"]),
    ("backend_dev", "Backend Developer", "Xây dựng API, nghiệp vụ và thao tác database.",
     STRONG_MODEL, 16000, ["fs.read", "fs.write:backend"]),
    ("frontend_dev", "Frontend Developer", "Xây dựng giao diện và kết nối API Backend.",
     STRONG_MODEL, 16000, ["fs.read", "fs.write:frontend"]),
    ("qa_tester", "QA Tester", "Xây dựng test case, thực thi kiểm thử, báo cáo lỗi.",
     DEFAULT_MODEL, 12000, ["fs.read", "fs.write:tests", "cmd.run"]),
    ("code_reviewer", "Code Reviewer & Debugger", "Đánh giá chất lượng, bảo mật, phân tích và sửa lỗi.",
     STRONG_MODEL, 16000, ["fs.read", "fs.write:backend", "fs.write:frontend", "fs.write:tests", "cmd.run"]),
]

# SQL Server ISJSON() only accepts objects/arrays, so each setting value is an object
SETTINGS = {
    "limits": {
        "max_task_attempts": 3,
        "max_fix_iterations": 3,
        "command_timeout_seconds": 120,
        "default_run_budget_usd": 2.0,
    },
}

agents_table = sa.table(
    "agents",
    sa.column("code", sa.Unicode),
    sa.column("name", sa.Unicode),
    sa.column("role_description", sa.UnicodeText),
    sa.column("model", sa.Unicode),
    sa.column("max_output_tokens", sa.Integer),
)
settings_table = sa.table("app_settings", sa.column("key", sa.Unicode), sa.column("value", sa.UnicodeText))


def upgrade() -> None:
    op.bulk_insert(
        agents_table,
        [
            {"code": c, "name": n, "role_description": r, "model": m, "max_output_tokens": t}
            for c, n, r, m, t, _ in AGENTS
        ],
    )
    conn = op.get_bind()
    for code, *_, permissions in AGENTS:
        agent_id = conn.execute(sa.text("SELECT id FROM agents WHERE code = :c"), {"c": code}).scalar_one()
        for permission in permissions:
            conn.execute(
                sa.text("INSERT INTO agent_permissions (agent_id, permission) VALUES (:a, :p)"),
                {"a": agent_id, "p": permission},
            )
    op.bulk_insert(settings_table, [{"key": k, "value": json.dumps(v)} for k, v in SETTINGS.items()])


def downgrade() -> None:
    codes = [a[0] for a in AGENTS]
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM app_settings WHERE [key] IN :keys").bindparams(sa.bindparam("keys", expanding=True)),
        {"keys": list(SETTINGS)},
    )
    conn.execute(
        sa.text("DELETE FROM agents WHERE code IN :codes").bindparams(sa.bindparam("codes", expanding=True)),
        {"codes": codes},
    )
