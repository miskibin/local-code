from typing import ClassVar

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage


class _FakeCheckpointer:
    def __init__(self, msgs):
        self._msgs = msgs

    async def aget_tuple(self, _config):
        if self._msgs is None:
            return None

        class _Tup:
            checkpoint: ClassVar[dict] = {"channel_values": {"messages": self._msgs}}

        return _Tup()


class _FakeMCPRegistry:
    tools: ClassVar[list] = []


@pytest.fixture
async def app_with_msgs():
    from app.db import init_db
    from app.main import create_app

    app = create_app()
    await init_db()
    app.state.llm = object()
    app.state.mcp_registry = _FakeMCPRegistry()
    return app


@pytest.mark.asyncio
async def test_get_messages_no_checkpoint_returns_empty(app_with_msgs):
    app = app_with_msgs
    app.state.checkpointer = _FakeCheckpointer(None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/sessions/missing/messages")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_get_messages_returns_human_and_ai_text(app_with_msgs):
    app = app_with_msgs
    msgs = [
        SystemMessage(content="sys"),
        HumanMessage(id="u1", content="hi"),
        AIMessage(id="a1", content="hello"),
        AIMessage(id="a2", content=""),  # empty skipped
        ToolMessage(content="tool out", tool_call_id="t1"),  # skipped
    ]
    app.state.checkpointer = _FakeCheckpointer(msgs)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/sessions/s1/messages")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert body[0] == {"id": "u1", "role": "user", "parts": [{"type": "text", "text": "hi"}]}
    assert body[1] == {
        "id": "a1",
        "role": "assistant",
        "parts": [{"type": "text", "text": "hello"}],
    }


@pytest.mark.asyncio
async def test_get_messages_extracts_text_from_block_content(app_with_msgs):
    app = app_with_msgs
    msgs = [
        AIMessage(
            id="a1",
            content=[
                {"type": "text", "text": "part 1 "},
                {"type": "tool_use", "id": "x"},
                {"type": "text", "text": "part 2"},
            ],
        ),
    ]
    app.state.checkpointer = _FakeCheckpointer(msgs)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/sessions/s1/messages")
    assert r.json() == [
        {"id": "a1", "role": "assistant", "parts": [{"type": "text", "text": "part 1 part 2"}]}
    ]
