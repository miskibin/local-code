import pytest
from deepagents.middleware._tool_exclusion import _ToolExclusionMiddleware
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


def test_build_agent_extends_tool_exclusion_to_each_subagent(monkeypatch):
    """deepagents wraps the top-level agent with our `_ToolExclusionMiddleware`,
    but subagents dispatched through `task` build their own model call stack and
    inherit the parent tool roster — including built-ins like `ls`/`grep` that
    we excluded. Without the exclusion the subagent loops thousands of `ls`
    calls. Verify each subagent spec carries the same exclusion middleware."""
    from langgraph.checkpoint.memory import InMemorySaver

    from app.graphs import main_agent

    captured: dict = {}

    def fake_create_deep_agent(**kwargs):
        captured["subagents"] = kwargs.get("subagents")
        return object()

    monkeypatch.setattr(main_agent, "create_deep_agent", fake_create_deep_agent)
    subs = [
        {
            "name": "research-agent",
            "description": "d",
            "system_prompt": "p",
            "tools": [],
        },
        {
            "name": "sql-agent",
            "description": "d2",
            "system_prompt": "p2",
            "tools": [],
            "middleware": ["pre-existing"],
        },
    ]
    main_agent.build_agent(
        llm=_FakeChatWithTools(responses=[""]),
        tools=[],
        checkpointer=InMemorySaver(),
        subagents=subs,
    )
    captured_subs = captured["subagents"]
    assert len(captured_subs) == 2
    for s in captured_subs:
        mws = s.get("middleware") or []
        excl = [m for m in mws if isinstance(m, _ToolExclusionMiddleware)]
        assert excl, f"subagent {s['name']!r} missing _ToolExclusionMiddleware"
        assert excl[0]._excluded == main_agent._EXCLUDED_BUILTIN_TOOLS
    # Caller-supplied middleware list is preserved (not clobbered).
    sql_mws = captured_subs[1]["middleware"]
    assert "pre-existing" in sql_mws
