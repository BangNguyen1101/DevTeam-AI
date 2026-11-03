"""Schema-level guarantees on SQL Server (cascades, JSON checks)."""

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.models import Agent, Artifact, ExecutionEvent, Project, Task, TaskDependency, WorkflowRun


def _make_run(db) -> tuple[Project, WorkflowRun, Task, Task]:
    agent_id = db.scalar(select(Agent.id).where(Agent.code == "business_analyst"))
    project = Project(name="Schema test", workspace_dir="schema-test-0001")
    run = WorkflowRun(project=project, request_text="Xây dựng ứng dụng ghi chú")
    t1 = Task(run=run, agent_id=agent_id, task_key="ba", title="Phân tích", input_data={"lang": "vi"})
    t2 = Task(run=run, agent_id=agent_id, task_key="arch", title="Thiết kế")
    db.add_all([project, run, t1, t2])
    db.flush()
    db.add_all([
        TaskDependency(task_id=t2.id, depends_on_task_id=t1.id),
        Artifact(run_id=run.id, task_id=t1.id, kind="requirements", name="SRS", content="..."),
        ExecutionEvent(run_id=run.id, task_id=t1.id, event_type="task.completed", message="ok", data={"n": 1}),
    ])
    db.commit()
    return project, run, t1, t2


def test_json_round_trip(db):
    _, _, t1, _ = _make_run(db)
    db.expire_all()
    assert db.get(Task, t1.id).input_data == {"lang": "vi"}


def test_deleting_project_cascades_to_run_data(db):
    project, run, _, _ = _make_run(db)
    db.execute(text("DELETE FROM projects WHERE id = :id"), {"id": project.id})
    db.commit()
    for model in (WorkflowRun, Task, Artifact, ExecutionEvent):
        assert db.scalar(select(func.count()).select_from(model).where(model.run_id == run.id if model is not WorkflowRun else model.id == run.id)) == 0


def test_invalid_json_is_rejected_by_check_constraint(db):
    _, _, t1, _ = _make_run(db)
    with pytest.raises(IntegrityError):
        db.execute(text("UPDATE tasks SET input_data = N'not json' WHERE id = :id"), {"id": t1.id})
    db.rollback()


def test_task_cannot_depend_on_itself(db):
    _, _, t1, _ = _make_run(db)
    db.add(TaskDependency(task_id=t1.id, depends_on_task_id=t1.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
