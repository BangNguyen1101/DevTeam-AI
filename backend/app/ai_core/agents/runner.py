"""Runs one agent call through the OpenAI Agents SDK and reports its usage."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

import openai
from agents import Agent, AgentOutputSchema, ModelSettings, Runner
from pydantic import BaseModel

from app.ai_core.agents import prompts
from app.ai_core.llm.provider import ModelFactory

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)

# Structured-output agents answer in one turn; a small cap stops runaway loops
MAX_TURNS = 3

# Provider-side transient failures (rate limit, overload, timeouts) are waited out
# here instead of consuming the task's attempts. Free tiers hit these often.
TRANSIENT_ERRORS = (openai.RateLimitError, openai.InternalServerError, openai.APITimeoutError, openai.APIConnectionError)
BACKOFF_SECONDS: Sequence[float] = (5, 15, 30, 60, 90)

OnRetry = Callable[[Exception, float, int], Awaitable[None]]


class QuotaExhaustedError(Exception):
    """The provider's daily quota for this model is used up; waiting minutes won't help."""

    def __init__(self, model: str):
        super().__init__(f"Model '{model}' đã hết quota trong ngày của nhà cung cấp. Đổi model của agent trong Cài đặt.")
        self.model = model


def _is_daily_quota(exc: Exception) -> bool:
    # Gemini: quotaId "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
    return isinstance(exc, openai.RateLimitError) and "PerDay" in str(getattr(exc, "body", "") or exc)


@dataclass
class AgentCall(Generic[T]):
    output: T
    model: str
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    requests: int
    latency_ms: int


@dataclass
class AgentProfile:
    """The DB-configured parts of an agent needed to call it."""

    code: str
    name: str
    model: str
    max_output_tokens: int
    instructions: str | None


def build_instructions(profile: AgentProfile, base: str | None = None) -> str:
    text = base or prompts.BY_AGENT[profile.code]
    if profile.instructions:
        text += f"\n\nChỉ dẫn bổ sung từ người dùng:\n{profile.instructions}"
    return text


async def call_agent(
    profile: AgentProfile,
    prompt: str,
    output_type: type[T],
    model_factory: ModelFactory,
    instructions: str | None = None,
    on_retry: OnRetry | None = None,
    backoff: Sequence[float] | None = None,
) -> AgentCall[T]:
    agent = Agent(
        name=profile.name,
        instructions=build_instructions(profile, instructions),
        model=model_factory(profile.model),
        model_settings=ModelSettings(max_tokens=profile.max_output_tokens),
        # Non-strict schema: Gemini's compatible endpoint rejects some strict-mode keywords
        output_type=AgentOutputSchema(output_type, strict_json_schema=False),
    )
    delays = BACKOFF_SECONDS if backoff is None else backoff
    for retry in range(len(delays) + 1):
        started = time.perf_counter()  # latency of the successful call only
        try:
            result = await Runner.run(agent, prompt, max_turns=MAX_TURNS)
            break
        except TRANSIENT_ERRORS as exc:
            if _is_daily_quota(exc):
                raise QuotaExhaustedError(profile.model) from exc
            if retry == len(delays):
                raise
            delay = delays[retry]
            logger.warning("%s: %s, retrying in %ss", profile.code, type(exc).__name__, delay)
            if on_retry:
                await on_retry(exc, delay, retry + 1)
            await asyncio.sleep(delay)
    usage = result.context_wrapper.usage
    cached = getattr(usage.input_tokens_details, "cached_tokens", 0) or 0
    return AgentCall(
        output=result.final_output_as(output_type, raise_if_incorrect_type=True),
        model=profile.model,
        input_tokens=usage.input_tokens,
        cached_input_tokens=cached,
        output_tokens=usage.output_tokens,
        requests=usage.requests,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
