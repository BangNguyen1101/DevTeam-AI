from pydantic import BaseModel, ConfigDict, field_validator


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    role_description: str
    model: str
    max_output_tokens: int
    is_enabled: bool
    permissions: list[str]

    @field_validator("permissions", mode="before")
    @classmethod
    def flatten_permissions(cls, value: list) -> list[str]:
        return sorted(p if isinstance(p, str) else p.permission for p in value)
