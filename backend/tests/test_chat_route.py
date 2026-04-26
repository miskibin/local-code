import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel


class _FakeChatWithTools(FakeListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


@pytest.mark.asyncio
async def test_chat_route_returns_sse_with_protocol_header():
    from app.main import create_app
    from app.graphs.main_agent import build_agent
    from langgraph.checkpoint.memory import InMemorySaver

    app = create_app()
    app.state.graph = build_agent(
        llm=_FakeChatWithTools(responses=["yo"]),
        tools=[],
        checkpointer=InMemorySaver(),
    )

    payload = {
        "id": "thread-x",
        "messages": [{"id": "u1", "role": "user", "parts": [{"type": "text", "text": "ping"}]}],
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/chat", json=payload)
    assert r.status_code == 200
    assert r.headers["x-vercel-ai-ui-message-stream"] == "v1"
    assert r.headers["content-type"].startswith("text/event-stream")
    assert "[DONE]" in r.text
    assert '"type":"text-delta"' in r.text
