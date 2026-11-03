from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.agent import AgentRead, AgentUpdate
from app.services.agent import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentRead])
def list_agents(db: DbSession):
    return AgentService(db).list()


@router.patch("/{agent_id}", response_model=AgentRead)
def update_agent(agent_id: int, data: AgentUpdate, db: DbSession):
    return AgentService(db).update(agent_id, data)
