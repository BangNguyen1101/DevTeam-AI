from fastapi import APIRouter

from app.api.v1 import agents, analytics, projects, system, workflow

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(system.router)
api_router.include_router(projects.router)
# analytics first so GET /agents/stats is not shadowed by future /agents/{id} routes
api_router.include_router(analytics.router)
api_router.include_router(agents.router)
api_router.include_router(workflow.router)
