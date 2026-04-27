"""Pydantic shadow schema for recorded LangChain message chunks.

Captures only the fields `app/streaming.py` actually reads — `content`,
`tool_call_chunks`, `tool_calls`, `response_metadata.finish_reason`,
`usage_metadata`. `model_config = ConfigDict(extra="forbid")` makes any new
top-level field added by upstream LangChain a *capture-time* failure (in
`record.py`), forcing a deliberate update rather than silently dropping the
new field at test time.

Tests load fixtures with `RecordedChunk.model_validate_json(...)`. If the
shape stops matching, validation fails and the canary test
(`test_recorded_chunks_replay.py`) fails — surfacing drift loudly.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ToolCallChunkShape(BaseModel):
    """Mirror of langchain `ToolCallChunk` (the `tool_call_chunks` element)."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    name: str | None = None
    args: str | None = None
    index: int | None = None
    type: Literal["tool_call_chunk"] | None = None


class ToolCallShape(BaseModel):
    """Mirror of langchain `ToolCall` (the `tool_calls` element)."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    type: Literal["tool_call"] | None = None


class ResponseMetadata(BaseModel):
    """Subset of response_metadata fields the streamer reads. `extra="allow"`
    here so providers can add arbitrary keys (model name, safety ratings,
    etc.) without breaking validation — but the canonical fields the streamer
    cares about are typed."""

    model_config = ConfigDict(extra="allow")

    finish_reason: str | None = None
    stop_reason: str | None = None
    model_name: str | None = None


class UsageMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class ContentBlock(BaseModel):
    """A single content block in `list[dict]` content (Gemini-style)."""

    model_config = ConfigDict(extra="allow")  # signed-response `extras` etc.

    type: str | None = None
    text: str | None = None


class RecordedChunk(BaseModel):
    """One captured chunk from `model.astream(messages)`.

    `kind` discriminates which `BaseMessage` subclass to hydrate when replaying
    (always `AIMessageChunk` in practice today, but pinned so a future capture
    of `AIMessage` or `ToolMessage` is explicit).
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["AIMessageChunk", "AIMessage", "ToolMessage"]
    content: str | list[ContentBlock] = ""
    tool_call_chunks: list[ToolCallChunkShape] = Field(default_factory=list)
    tool_calls: list[ToolCallShape] = Field(default_factory=list)
    response_metadata: ResponseMetadata = Field(default_factory=ResponseMetadata)
    usage_metadata: UsageMetadata | None = None


class FixtureFile(BaseModel):
    """Top-of-file metadata that the canary test reads to know how to drive
    the replay (e.g. node attribution, expected outcome). One per JSONL file
    as the first line — subsequent lines are `RecordedChunk` records."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["fixture_meta"] = "fixture_meta"
    provider: str
    model: str
    prompt: str
    description: str
    captured_at: str  # ISO-8601
    captured_by: str  # "record.py" or "hand-authored"
    expected_text_nonempty: bool = True
