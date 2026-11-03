from fastapi import APIRouter

from app.api.v1 import agents, projects, system

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(system.router)
api_router.include_router(projects.router)
api_router.include_router(agents.router)
