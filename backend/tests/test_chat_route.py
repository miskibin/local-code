import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel


class _FakeChatWithTools(FakeListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


@pytest.mark.asyncio
async def test_chat_route_returns_sse_with_protocol_header():
    from langgraph.checkpoint.memory import InMemorySaver

    from app.db import init_db
    from app.main import create_app

    app = create_app()
    await init_db()
    app.state.llm_cache = {"test-model": _FakeChatWithTools(responses=["yo"])}
    app.state.checkpointer = InMemorySaver()
    app.state.mcp_tools = []

    payload = {
        "id": "thread-x",
        "model": "test-model",
        "messages": [{"id": "u1", "role": "user", "parts": [{"type": "text", "text": "ping"}]}],
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers={"X-User-Email": "test@example.com"}
    ) as ac:
        r = await ac.post("/chat", json=payload)
    assert r.status_code == 200
    assert r.headers["x-vercel-ai-ui-message-stream"] == "v1"
    assert r.headers["content-type"].startswith("text/event-stream")
    assert "[DONE]" in r.text
    assert '"type":"text-delta"' in r.text
