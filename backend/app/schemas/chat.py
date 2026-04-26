from typing import Literal

from pydantic import BaseModel


class TextPart(BaseModel):
    type: Literal["text"]
    text: str


class UIMessage(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    parts: list[TextPart]


class ChatRequest(BaseModel):
    id: str
    messages: list[UIMessage]
    reset: bool = False
    model: str

    def to_lc_messages(self) -> list[tuple[str, str]]:
        return [(m.role, "".join(p.text for p in m.parts)) for m in self.messages]
