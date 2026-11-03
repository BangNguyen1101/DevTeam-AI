from fastapi import APIRouter

from app.api.deps import DbSession
from app.repositories.agent import AgentRepository
from app.schemas.agent import AgentRead

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentRead])
def list_agents(db: DbSession):
    return AgentRepository(db).list()
