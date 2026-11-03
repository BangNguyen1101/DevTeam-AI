from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentUpdate(BaseModel):
    model: str | None = Field(default=None, min_length=1, max_length=100)
    max_output_tokens: int | None = Field(default=None, ge=256, le=128_000)
    is_enabled: bool | None = None
    instructions: str | None = Field(default=None, max_length=20_000)


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    role_description: str
    model: str
    max_output_tokens: int
    is_enabled: bool
    instructions: str | None
    permissions: list[str]

    @field_validator("permissions", mode="before")
    @classmethod
    def flatten_permissions(cls, value: list) -> list[str]:
        return sorted(p if isinstance(p, str) else p.permission for p in value)
