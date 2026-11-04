from fastapi import APIRouter, Depends

from app.api.deps import require_user
from app.api.v1 import agents, analytics, auth, projects, system, workflow

api_router = APIRouter(prefix="/api/v1")
# Public: health check and login
api_router.include_router(system.router)
api_router.include_router(auth.router)

# Everything else requires a signed-in user
protected = [Depends(require_user)]
api_router.include_router(projects.router, dependencies=protected)
# analytics first so GET /agents/stats is not shadowed by future /agents/{id} routes
api_router.include_router(analytics.router, dependencies=protected)
api_router.include_router(agents.router, dependencies=protected)
api_router.include_router(workflow.router, dependencies=protected)
