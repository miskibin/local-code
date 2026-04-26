from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _now_utc() -> datetime:
    return datetime.now(UTC)


class ChatSession(SQLModel, table=True):
    id: str = Field(primary_key=True)
    title: str = ""
    created_at: datetime = Field(default_factory=_now_utc)


class ChatMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="chatsession.id", index=True)
    role: str
    content: str
    created_at: datetime = Field(default_factory=_now_utc)


class MCPServerConfig(SQLModel, table=True):
    name: str = Field(primary_key=True)
    enabled: bool = True
    connection: dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)


class ToolFlag(SQLModel, table=True):
    name: str = Field(primary_key=True)
    enabled: bool = True


class SavedArtifact(SQLModel, table=True):
    id: str = Field(primary_key=True)
    session_id: str | None = Field(default=None, index=True)
    kind: str
    title: str
    payload: dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)
    summary: str = ""
    source_kind: str | None = None
    source_code: str | None = None
    parent_artifact_ids: list[str] = Field(sa_column=Column(JSON), default_factory=list)
    payload_size: int = 0
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class SavedTask(SQLModel, table=True):
    id: str = Field(primary_key=True)
    title: str
    description: str = ""
    source_session_id: str | None = None
    variables: list[dict[str, Any]] = Field(sa_column=Column(JSON), default_factory=list)
    steps: list[dict[str, Any]] = Field(sa_column=Column(JSON), default_factory=list)
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)
