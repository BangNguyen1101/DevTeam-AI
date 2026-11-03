from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.schemas.analytics import AgentStats, DashboardSummary, Limits, ModelPrice, SettingsRead, UsageSummary
from app.services.analytics import AnalyticsService
from app.services.settings import SettingsService

router = APIRouter(tags=["analytics"])


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(db: DbSession):
    return AnalyticsService(db).dashboard()


@router.get("/usage/summary", response_model=UsageSummary)
def usage_summary(db: DbSession, days: int = Query(7, ge=1, le=365), project_id: int | None = None):
    return AnalyticsService(db).usage_summary(days, project_id)


@router.get("/agents/stats", response_model=list[AgentStats])
def agent_stats(db: DbSession):
    return AnalyticsService(db).agent_stats()


@router.get("/settings", response_model=SettingsRead)
def read_settings(db: DbSession):
    return SettingsService(db).read()


@router.put("/settings/limits", response_model=SettingsRead)
def update_limits(data: Limits, db: DbSession):
    return SettingsService(db).update_limits(data)


@router.put("/settings/pricing", response_model=SettingsRead)
def update_pricing(data: dict[str, ModelPrice], db: DbSession):
    return SettingsService(db).update_pricing(data)
