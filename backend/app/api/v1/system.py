import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import DbSession

router = APIRouter(tags=["system"])
logger = logging.getLogger(__name__)


@router.get("/health")
def health(db: DbSession):
    """Liveness + database connectivity check."""
    try:
        version = db.execute(text("SELECT CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(50))")).scalar_one()
        migration = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    except Exception as exc:
        logger.exception("Health check failed")
        return JSONResponse(status_code=503, content={"status": "error", "database": {"ok": False, "error": type(exc).__name__}})
    return {"status": "ok", "database": {"ok": True, "server_version": version, "migration": migration}}
