from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.utils import now_utc


class User(SQLModel, table=True):
    id: str = Field(primary_key=True)
    email: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=now_utc)


class ChatSession(SQLModel, table=True):
    id: str = Field(primary_key=True)
    owner_id: str = Field(foreign_key="user.id", index=True)
    title: str = ""
    created_at: datetime = Field(default_factory=now_utc)
    is_pinned: bool = Field(default=False, index=True)
    pinned_at: datetime | None = None
    task_id: str | None = Field(default=None, index=True)


class ChatMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="chatsession.id", index=True)
    role: str
    content: str
    created_at: datetime = Field(default_factory=now_utc)


class MessageTrace(SQLModel, table=True):
    ai_message_id: str = Field(primary_key=True)
    session_id: str = Field(foreign_key="chatsession.id", index=True)
    trace_id: str
    created_at: datetime = Field(default_factory=now_utc)


class MCPServerConfig(SQLModel, table=True):
    name: str = Field(primary_key=True)
    enabled: bool = True
    connection: dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)


class MCPServerUserFlag(SQLModel, table=True):
    user_id: str = Field(primary_key=True, foreign_key="user.id")
    name: str = Field(primary_key=True)
    enabled: bool = True


class ToolFlag(SQLModel, table=True):
    user_id: str = Field(primary_key=True, foreign_key="user.id")
    name: str = Field(primary_key=True)
    enabled: bool = True


class SkillFlag(SQLModel, table=True):
    user_id: str = Field(primary_key=True, foreign_key="user.id")
    name: str = Field(primary_key=True)
    enabled: bool = True


class SavedArtifact(SQLModel, table=True):
    id: str = Field(primary_key=True)
    owner_id: str = Field(foreign_key="user.id", index=True)
    session_id: str | None = Field(default=None, index=True)
    kind: str
    title: str
    payload: dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)
    summary: str = ""
    source_kind: str | None = None
    source_code: str | None = None
    parent_artifact_ids: list[str] = Field(sa_column=Column(JSON), default_factory=list)
    payload_size: int = 0
    pinned: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class SavedTask(SQLModel, table=True):
    id: str = Field(primary_key=True)
    owner_id: str = Field(foreign_key="user.id", index=True)
    title: str
    description: str = ""
    source_session_id: str | None = None
    variables: list[dict[str, Any]] = Field(sa_column=Column(JSON), default_factory=list)
    steps: list[dict[str, Any]] = Field(sa_column=Column(JSON), default_factory=list)
    tags: list[str] = Field(sa_column=Column(JSON), default_factory=list)
    role: str | None = None
    creator: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
