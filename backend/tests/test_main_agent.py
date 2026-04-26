import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel


class _FakeChatWithTools(FakeListChatModel):
    """FakeListChatModel that no-ops bind_tools so deepagents middleware can inject tools."""

    def bind_tools(self, tools, **kwargs):
        return self


def test_build_agent_compiles_with_no_tools():
    from langgraph.checkpoint.memory import InMemorySaver

    from app.graphs.main_agent import build_agent
    llm = _FakeChatWithTools(responses=["hello"])
    graph = build_agent(llm=llm, tools=[], checkpointer=InMemorySaver())
    assert hasattr(graph, "astream")


@pytest.mark.asyncio
async def test_build_agent_streams_text_from_model_node():
    from langgraph.checkpoint.memory import InMemorySaver

    from app.graphs.main_agent import build_agent
    llm = _FakeChatWithTools(responses=["hi there"])
    graph = build_agent(llm=llm, tools=[], checkpointer=InMemorySaver())
    tokens: list[str] = []
    async for chunk, meta in graph.astream(
        {"messages": [("user", "hi")]},
        stream_mode="messages",
        config={"configurable": {"thread_id": "t1"}},
    ):
        if meta.get("langgraph_node") == "model" and getattr(chunk, "content", ""):
            tokens.append(chunk.content)
    assert "".join(tokens) == "hi there"
