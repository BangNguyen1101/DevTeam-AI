from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import Agent
from app.realtime.hub import hub
from app.repositories.agent import AgentRepository
from app.schemas.agent import AgentRead, AgentUpdate


class AgentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AgentRepository(db)

    def list(self) -> list[Agent]:
        return self.repo.list()

    def update(self, agent_id: int, data: AgentUpdate) -> Agent:
        agent = self.repo.get(agent_id)
        if agent is None:
            raise NotFoundError(f"Agent {agent_id} not found")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(agent, field, value)
        self.db.commit()
        agent = self.repo.get(agent_id)
        hub.publish_threadsafe("agents", "agent.updated", AgentRead.model_validate(agent).model_dump(mode="json"))
        return agent
