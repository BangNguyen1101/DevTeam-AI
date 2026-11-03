from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Agent


class AgentRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[Agent]:
        stmt = select(Agent).options(selectinload(Agent.permissions)).order_by(Agent.id)
        return list(self.db.scalars(stmt))

    def get(self, agent_id: int) -> Agent | None:
        stmt = select(Agent).options(selectinload(Agent.permissions)).where(Agent.id == agent_id)
        return self.db.scalar(stmt.execution_options(populate_existing=True))
