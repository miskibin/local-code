from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

VariableType = Literal["string", "number", "boolean"]
StepKind = Literal["tool", "code", "subagent", "prompt"]
OutputKind = Literal["rows", "text", "chart", "json", "file"]


class TaskVariable(BaseModel):
    name: str
    type: VariableType = "string"
    label: str = ""
    default: Any = None
    required: bool = True


class StepInputRef(BaseModel):
    name: str
    source: Literal["var", "step"]
    ref: str


class TaskStep(BaseModel):
    id: str
    kind: StepKind
    title: str
    server: str | None = None
    tool: str | None = None
    args_template: dict[str, Any] | None = None
    code: str | None = None
    subagent: str | None = None
    prompt: str | None = None
    output_name: str = "output"
    output_kind: OutputKind = "text"
    inputs: list[StepInputRef] = Field(default_factory=list)


class TaskDTO(BaseModel):
    id: str
    title: str
    description: str = ""
    source_session_id: str | None = None
    variables: list[TaskVariable] = Field(default_factory=list)
    steps: list[TaskStep] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TaskListItem(BaseModel):
    id: str
    title: str
    description: str = ""
    updated_at: datetime | None = None


class GenerateTaskRequest(BaseModel):
    session_id: str
    message_id: str | None = None
    model: str


class TaskRunSpec(BaseModel):
    task_id: str
    variables: dict[str, Any] = Field(default_factory=dict)
