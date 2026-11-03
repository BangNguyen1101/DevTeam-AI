"""Builds Agents SDK models for any OpenAI Chat Completions compatible endpoint
(OpenAI, Gemini's OpenAI-compatible API, ...)."""

from collections.abc import Callable
from functools import lru_cache

from agents import Model, OpenAIChatCompletionsModel, set_tracing_disabled
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.exceptions import AppError

# Traces would be exported to the OpenAI platform, which fails with non-OpenAI keys
# and would ship prompts off-box; execution history lives in our own DB instead.
set_tracing_disabled(True)

ModelFactory = Callable[[str], Model]


class LlmNotConfiguredError(AppError):
    status_code = 503
    code = "llm_not_configured"


@lru_cache
def _client() -> AsyncOpenAI:
    config = get_settings()
    if not config.llm_key:
        raise LlmNotConfiguredError("LLM_API_KEY chưa được cấu hình trong backend/.env")
    # No client-side retries: call_agent owns retry/backoff (and reports it as events).
    # Stacked retries x 180s timeouts made one overloaded provider stall a run for ~9 minutes.
    return AsyncOpenAI(api_key=config.llm_key, base_url=config.llm_base_url or None, max_retries=0, timeout=120)


def llm_configured() -> bool:
    return bool(get_settings().llm_key)


def default_model_factory(model_name: str) -> Model:
    return OpenAIChatCompletionsModel(model=model_name, openai_client=_client())


async def list_models() -> list[str]:
    page = await _client().models.list()
    # Gemini prefixes ids with "models/"; the chat endpoint accepts the bare name
    return sorted({m.id.removeprefix("models/") async for m in page})
