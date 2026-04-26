from datetime import UTC, datetime
from typing import Any
from sqlalchemy import Column, JSON
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
