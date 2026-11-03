from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Agent


class AgentRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[Agent]:
        stmt = select(Agent).options(selectinload(Agent.permissions)).order_by(Agent.id)
        return list(self.db.scalars(stmt))
