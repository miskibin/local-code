import base64
from pathlib import Path
from typing import Annotated, Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.artifact_store import get_artifacts
from app.models import SavedArtifact
from app.services.table_summary import build_table_summary


class TextPart(BaseModel):
    type: Literal["text"]
    text: str


class FilePart(BaseModel):
    type: Literal["file"]
    artifact_id: str = Field(alias="artifactId")
    media_type: str = Field(alias="mediaType")
    name: str | None = None

    model_config = {"populate_by_name": True}


MessagePart = Annotated[TextPart | FilePart, Field(discriminator="type")]


class UIMessage(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    parts: list[MessagePart]


class TaskRunSpec(BaseModel):
    task_id: str
    variables: dict[str, Any] = Field(default_factory=dict)


class ResumeSpec(BaseModel):
    tool_call_id: str = Field(alias="toolCallId")
    value: str

    model_config = {"populate_by_name": True}


class ChatRequest(BaseModel):
    id: str
    messages: list[UIMessage]
    reset: bool = False
    model: str
    task_run: TaskRunSpec | None = None
    resume: ResumeSpec | None = None

    async def to_lc_messages(self, *, last_only: bool = False) -> list[BaseMessage]:
        msgs = self.messages[-1:] if last_only and self.messages else self.messages
        # Single batched DB lookup for all FilePart artifacts in this turn,
        # so attachment-heavy messages don't fan out N serial queries on the
        # /chat hot path before streaming starts.
        attachment_ids = [
            part.artifact_id
            for m in msgs
            for part in m.parts
            if isinstance(part, FilePart)
        ]
        artifact_cache = await get_artifacts(attachment_ids)
        out: list[BaseMessage] = []
        for m in msgs:
            blocks: list[dict[str, Any]] = []
            text_buf: list[str] = []
            for part in m.parts:
                if isinstance(part, TextPart):
                    text_buf.append(part.text)
                else:
                    block = _file_part_to_block(part, artifact_cache.get(part.artifact_id))
                    if block is None:
                        continue
                    if block["type"] == "text":
                        text_buf.append(block["text"])
                    else:
                        blocks.append(block)
            if text_buf:
                blocks.append({"type": "text", "text": "".join(text_buf)})
            content: Any = (
                blocks
                if any(b["type"] != "text" for b in blocks)
                else ("".join(b["text"] for b in blocks if b["type"] == "text"))
            )
            out.append(_make_message(m.role, content))
        return out


def _make_message(role: str, content: Any) -> BaseMessage:
    if role == "user":
        return HumanMessage(content=content)
    if role == "assistant":
        return AIMessage(content=content)
    return SystemMessage(content=content)


def _file_part_to_block(
    part: FilePart, artifact: SavedArtifact | None
) -> dict[str, Any] | None:
    if artifact is None:
        return {"type": "text", "text": f"\n[missing attachment {part.artifact_id}]\n"}
    media = part.media_type or (artifact.payload or {}).get("mime", "")
    if media.startswith("image/"):
        path = (artifact.payload or {}).get("path")
        if not path or not Path(path).exists():
            return {"type": "text", "text": f"\n[missing image file for {part.artifact_id}]\n"}
        data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
        return {
            "type": "image",
            "source_type": "base64",
            "data": data,
            "mime_type": media,
        }
    if artifact.kind == "table" or media in {
        "text/csv",
        "application/csv",
        "text/tab-separated-values",
    }:
        summary = build_table_summary(artifact)
        return {
            "type": "text",
            "text": f"\n\n[Attached table — artifact:{artifact.id}]\n{summary}\n",
        }
    if artifact.kind == "text":
        text = (artifact.payload or {}).get("text_preview") or (artifact.payload or {}).get(
            "text", ""
        )
        return {
            "type": "text",
            "text": f"\n\n[Attached text — artifact:{artifact.id}]\n{text}\n",
        }
    return {"type": "text", "text": f"\n[attached artifact {artifact.id} ({artifact.kind})]\n"}
