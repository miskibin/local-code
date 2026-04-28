import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.tools import tool


@tool
def chat_stub_tool(x: int) -> int:
    """stub"""
    return x


@pytest.mark.asyncio
async def test_chat_skips_disabled_tool(monkeypatch):
    """When a tool flag is False, the agent rebuild for that turn must not include it."""
    from app import tool_registry
    from app.db import async_session, init_db
    from app.main import create_app
    from app.models import ToolFlag

    monkeypatch.setattr(tool_registry, "discover_tools", lambda: [chat_stub_tool])

    captured: list[list] = []

    def fake_build_agent(
        *,
        llm,
        tools,
        checkpointer,
        subagents=None,
        enabled_skills=None,
        custom_instructions="",
    ):
        captured.append([t.name for t in tools])
        from app.graphs.main_agent import build_agent as real

        return real(
            llm=llm,
            tools=tools,
            checkpointer=checkpointer,
            subagents=subagents,
            enabled_skills=enabled_skills,
            custom_instructions=custom_instructions,
        )

    monkeypatch.setattr("app.routes.chat.build_agent_for_turn", fake_build_agent)

    from tests.conftest import TEST_OWNER_ID, ensure_test_user

    app = create_app()
    await init_db()
    await ensure_test_user()
    async with async_session() as s:
        s.add(ToolFlag(user_id=TEST_OWNER_ID, name="chat_stub_tool", enabled=False))
        await s.commit()

    # Pre-attach a fake LLM + checkpointer via app.state
    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    from langgraph.checkpoint.memory import InMemorySaver

    class _FakeChatWithTools(FakeListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    app.state.llm_cache = {"test-model": _FakeChatWithTools(responses=["ok"])}
    app.state.checkpointer = InMemorySaver()

    payload = {
        "id": "t1",
        "model": "test-model",
        "messages": [{"id": "u1", "role": "user", "parts": [{"type": "text", "text": "hi"}]}],
    }
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"X-User-Email": "test@example.com"},
        ) as ac:
            await ac.post("/chat", json=payload)

        assert captured and captured[0] == []  # tool was filtered out
    finally:
        from sqlmodel import delete

        async with async_session() as s:
            await s.execute(delete(ToolFlag).where(ToolFlag.name == "chat_stub_tool"))
            await s.commit()
