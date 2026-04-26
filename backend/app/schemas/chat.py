from typing import Any, Literal

from pydantic import BaseModel, Field


class TextPart(BaseModel):
    type: Literal["text"]
    text: str


class UIMessage(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    parts: list[TextPart]


class TaskRunSpec(BaseModel):
    task_id: str
    variables: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    id: str
    messages: list[UIMessage]
    reset: bool = False
    model: str
    task_run: TaskRunSpec | None = None

    def to_lc_messages(self) -> list[tuple[str, str]]:
        return [(m.role, "".join(p.text for p in m.parts)) for m in self.messages]
