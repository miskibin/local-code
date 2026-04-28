from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

VariableType = Literal["string", "number", "boolean"]
StepKind = Literal["tool", "code", "subagent", "prompt", "report"]
OutputKind = Literal["rows", "text", "chart", "json", "file"]


class TaskVariable(BaseModel):
    name: str
    type: VariableType = "string"
    label: str = ""
    default: Any = None
    required: bool = True


class TaskStep(BaseModel):
    model_config = {"extra": "ignore"}

    id: str
    kind: StepKind
    title: str
    tool: str | None = None
    args_template: dict[str, Any] | None = None
    code: str | None = None
    subagent: str | None = None
    prompt: str | None = None
    output_name: str = "output"
    output_kind: OutputKind = "text"


class TaskDTO(BaseModel):
    id: str
    title: str
    description: str = ""
    source_session_id: str | None = None
    variables: list[TaskVariable] = Field(default_factory=list)
    steps: list[TaskStep] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    role: str | None = None
    creator: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TaskListItem(BaseModel):
    id: str
    title: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    role: str | None = None
    creator: str | None = None
    updated_at: datetime | None = None


class GenerateTaskRequest(BaseModel):
    session_id: str
    model: str
