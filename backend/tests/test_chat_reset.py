from typing import ClassVar

import pytest
from httpx import ASGITransport, AsyncClient


class _FakeCheckpointer:
    def __init__(self):
        self.deleted: list[str] = []

    async def adelete_thread(self, thread_id: str) -> None:
        self.deleted.append(thread_id)


class _FakeMCPRegistry:
    tools: ClassVar[list] = []


def _empty_stream_chat(**_kwargs):
    async def _agen():
        if False:
            yield ""

    return _agen()


def _fake_build_agent(**_kwargs):
    return object()


@pytest.fixture
async def chat_app(monkeypatch):
    from app.db import init_db
    from app.main import create_app
    from app.routes import chat as chat_module

    monkeypatch.setattr(chat_module, "stream_chat", _empty_stream_chat)
    monkeypatch.setattr(chat_module, "build_agent_for_turn", _fake_build_agent)

    app = create_app()
    await init_db()
    cp = _FakeCheckpointer()
    app.state.checkpointer = cp
    app.state.llm_cache = {"test-model": object()}
    app.state.mcp_registry = _FakeMCPRegistry()
    return app, cp


@pytest.mark.asyncio
async def test_chat_reset_true_deletes_thread(chat_app):
    app, cp = chat_app
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers={"X-User-Email": "test@example.com"}
    ) as ac:
        r = await ac.post(
            "/chat",
            json={
                "id": "sess-reset",
                "model": "test-model",
                "messages": [
                    {"id": "m1", "role": "user", "parts": [{"type": "text", "text": "hi"}]}
                ],
                "reset": True,
            },
        )
        assert r.status_code == 200
    assert cp.deleted == ["sess-reset"]


@pytest.mark.asyncio
async def test_chat_reset_default_false_keeps_thread(chat_app):
    app, cp = chat_app
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers={"X-User-Email": "test@example.com"}
    ) as ac:
        r = await ac.post(
            "/chat",
            json={
                "id": "sess-keep",
                "model": "test-model",
                "messages": [
                    {"id": "m1", "role": "user", "parts": [{"type": "text", "text": "hi"}]}
                ],
            },
        )
        assert r.status_code == 200
    assert cp.deleted == []
