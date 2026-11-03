from datetime import date

from pydantic import BaseModel, Field


class UsageTotals(BaseModel):
    calls: int
    requests: int
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


class AgentUsage(BaseModel):
    agent_code: str
    agent_name: str
    calls: int
    total_tokens: int
    cost_usd: float
    avg_latency_ms: float | None


class DailyUsage(BaseModel):
    day: date
    total_tokens: int
    cost_usd: float
    calls: int


class ModelUsage(BaseModel):
    model: str
    calls: int
    total_tokens: int
    cost_usd: float
    avg_latency_ms: float | None


class ProjectUsage(BaseModel):
    project_id: int
    project_name: str
    tasks_completed: int
    total_tokens: int
    cost_usd: float


class UsageSummary(BaseModel):
    days: int
    totals: UsageTotals
    by_agent: list[AgentUsage]
    by_day: list[DailyUsage]
    by_model: list[ModelUsage]
    by_project: list[ProjectUsage]
    monthly_budget_usd: float | None
    month_cost_usd: float


class AgentStats(BaseModel):
    agent_id: int
    agent_code: str
    tasks_total: int
    tasks_completed: int
    tasks_failed: int
    current_task_title: str | None
    current_task_status: str | None
    total_tokens: int
    cost_usd: float
    last_active_at: str | None


class ProjectProgress(BaseModel):
    project_id: int
    project_name: str
    latest_run_id: int | None
    latest_run_status: str | None
    tasks_total: int
    tasks_completed: int


class DashboardSummary(BaseModel):
    projects_total: int
    projects_active: int
    runs_active: int
    tasks_running: int
    tasks_completed: int
    tasks_failed: int
    task_success_rate: float | None
    agents_enabled: int
    agents_total: int
    total_tokens: int
    cost_usd: float
    monthly_budget_usd: float | None
    approvals_pending: int
    projects: list[ProjectProgress]


class Limits(BaseModel):
    max_task_attempts: int = Field(ge=1, le=10)
    max_fix_iterations: int = Field(ge=0, le=10)
    command_timeout_seconds: int = Field(ge=5, le=1800)
    default_run_budget_usd: float = Field(ge=0, le=1000)
    monthly_budget_usd: float | None = Field(default=None, ge=0, le=100000)
    # Running AI-generated code (tests) on this machine requires a human approval
    require_command_approval: bool = True
    # Code Reviewer always audits the code once tests pass (QA re-tests any change)
    mandatory_review: bool = True


class ModelPrice(BaseModel):
    """USD per 1M tokens, entered by the user from the provider's price list."""

    input_per_1m: float = Field(ge=0)
    cached_input_per_1m: float = Field(default=0, ge=0)
    output_per_1m: float = Field(ge=0)


class SettingsRead(BaseModel):
    limits: Limits
    pricing: dict[str, ModelPrice]
    llm_configured: bool
    llm_endpoint: str
