from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AppSetting
from app.realtime.hub import hub
from app.schemas.analytics import Limits, ModelPrice, SettingsRead

LIMITS_KEY = "limits"
PRICING_KEY = "pricing"


class SettingsService:
    def __init__(self, db: Session):
        self.db = db

    def _get(self, key: str, default: Any) -> Any:
        row = self.db.get(AppSetting, key)
        return row.value if row is not None else default

    def _put(self, key: str, value: Any) -> None:
        row = self.db.get(AppSetting, key)
        if row is None:
            self.db.add(AppSetting(key=key, value=value))
        else:
            row.value = value

    def limits(self) -> Limits:
        return Limits.model_validate(self._get(LIMITS_KEY, {}))

    def pricing(self) -> dict[str, ModelPrice]:
        return {model: ModelPrice.model_validate(p) for model, p in self._get(PRICING_KEY, {}).items()}

    def read(self) -> SettingsRead:
        config = get_settings()
        return SettingsRead(
            limits=self.limits(),
            pricing=self.pricing(),
            llm_configured=bool(config.llm_key),
            llm_endpoint=urlparse(config.llm_base_url).hostname or "api.openai.com",
        )

    def update_limits(self, limits: Limits) -> SettingsRead:
        self._put(LIMITS_KEY, limits.model_dump())
        self.db.commit()
        hub.publish_threadsafe("settings", "settings.updated", {"key": LIMITS_KEY})
        return self.read()

    def update_pricing(self, pricing: dict[str, ModelPrice]) -> SettingsRead:
        # Stored as an object (ISJSON rejects scalars) keyed by model name
        self._put(PRICING_KEY, {m: p.model_dump() for m, p in pricing.items()})
        self.db.commit()
        hub.publish_threadsafe("settings", "settings.updated", {"key": PRICING_KEY})
        return self.read()
