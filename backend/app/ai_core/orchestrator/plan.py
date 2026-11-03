"""Validation of the AI Manager's plan before it becomes tasks in the DB."""

import re

from app.ai_core.agents.outputs import Plan

KEY_PATTERN = re.compile(r"^[a-z0-9_]{1,40}$")
MAX_TASKS = 8


def validate_plan(plan: Plan, enabled_agents: set[str]) -> list[str]:
    """Return human-readable problems; an empty list means the plan is executable."""
    errors: list[str] = []
    tasks = plan.tasks
    if not tasks:
        return ["Kế hoạch không có tác vụ nào"]
    if len(tasks) > MAX_TASKS:
        errors.append(f"Tối đa {MAX_TASKS} tác vụ")

    keys = [t.key for t in tasks]
    if len(set(keys)) != len(keys):
        errors.append("Key tác vụ bị trùng")
    for t in tasks:
        if not KEY_PATTERN.match(t.key):
            errors.append(f"Key '{t.key}' không hợp lệ (chỉ a-z, 0-9, _)")
        if t.agent_code not in enabled_agents:
            errors.append(f"Agent '{t.agent_code}' không tồn tại hoặc đang tắt")
        for dep in t.depends_on:
            if dep not in keys:
                errors.append(f"Tác vụ '{t.key}' phụ thuộc key không tồn tại '{dep}'")
            if dep == t.key:
                errors.append(f"Tác vụ '{t.key}' tự phụ thuộc chính nó")

    agents = [t.agent_code for t in tasks]
    for code in ("business_analyst", "architect"):
        if code not in agents:
            errors.append(f"Kế hoạch phải có tác vụ cho {code}")
    if len(set(agents)) != len(agents):
        errors.append("Mỗi agent chỉ được giao tối đa 1 tác vụ")

    if not errors and _has_cycle({t.key: t.depends_on for t in tasks}):
        errors.append("Kế hoạch có chu trình phụ thuộc")
    return errors


def _has_cycle(graph: dict[str, list[str]]) -> bool:
    state: dict[str, int] = {}  # 1 = visiting, 2 = done

    def visit(node: str) -> bool:
        if state.get(node) == 1:
            return True
        if state.get(node) == 2:
            return False
        state[node] = 1
        if any(visit(d) for d in graph.get(node, [])):
            return True
        state[node] = 2
        return False

    return any(visit(n) for n in graph)
