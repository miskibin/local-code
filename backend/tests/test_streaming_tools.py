import json
import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage


class _FakeGraph:
    def __init__(self, items):
        self._items = items

    async def astream(self, *_args, **_kwargs):
        for item in self._items:
            yield item


@pytest.mark.asyncio
async def test_stream_emits_tool_events_for_consolidated_aimessage():
    from app.streaming import stream_chat

    items = [
        (
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call_1",
                        "name": "web_fetch",
                        "args": {"url": "https://example.com"},
                    }
                ],
            ),
            {"langgraph_node": "model"},
        ),
        (
            ToolMessage(content="Hello, world", tool_call_id="call_1", name="web_fetch"),
            {"langgraph_node": "tools"},
        ),
        (
            AIMessageChunk(content="Done."),
            {"langgraph_node": "model"},
        ),
    ]
    events = []
    async for line in stream_chat(
        graph=_FakeGraph(items), thread_id="t1", lc_messages=[("user", "go")]
    ):
        events.append(line)
    parsed = [
        json.loads(e.removeprefix("data: ").strip())
        for e in events
        if e.startswith("data: {")
    ]
    types = [e["type"] for e in parsed]
    assert "tool-input-start" in types
    assert "tool-input-available" in types
    assert "tool-output-available" in types
    starts = [e for e in parsed if e["type"] == "tool-input-start"]
    avail = [e for e in parsed if e["type"] == "tool-input-available"]
    out = [e for e in parsed if e["type"] == "tool-output-available"]
    assert starts[0]["toolCallId"] == "call_1"
    assert starts[0]["toolName"] == "web_fetch"
    assert avail[0]["input"] == {"url": "https://example.com"}
    assert out[0]["output"] == "Hello, world"
    # ordering: start before available before output
    i_start = types.index("tool-input-start")
    i_avail = types.index("tool-input-available")
    i_out = types.index("tool-output-available")
    assert i_start < i_avail < i_out


@pytest.mark.asyncio
async def test_subagent_inner_tool_events_pass_through_namespace():
    """Tool events from a subagent (non-empty namespace) flow to the client,
    while subagent's internal LLM tokens stay out of the user-visible text."""
    from app.streaming import stream_chat
    from langchain_core.messages import AIMessageChunk

    items = [
        # Parent emits text
        ((), (AIMessageChunk(content="working"), {"langgraph_node": "model"})),
        # Subagent's internal LLM token — should NOT become text-delta
        (
            ("subagent:research",),
            (AIMessageChunk(content="thinking"), {"langgraph_node": "model"}),
        ),
        # Subagent calls a tool — SHOULD emit events
        (
            ("subagent:research",),
            (
                AIMessage(
                    content="",
                    tool_calls=[
                        {"id": "sub_1", "name": "web_fetch", "args": {"url": "https://x"}}
                    ],
                ),
                {"langgraph_node": "model"},
            ),
        ),
        (
            ("subagent:research",),
            (
                ToolMessage(content="ok", tool_call_id="sub_1", name="web_fetch"),
                {"langgraph_node": "tools"},
            ),
        ),
    ]
    events = []
    async for line in stream_chat(
        graph=_FakeGraph(items), thread_id="t1", lc_messages=[("user", "go")]
    ):
        events.append(line)
    parsed = [
        json.loads(e.removeprefix("data: ").strip())
        for e in events
        if e.startswith("data: {")
    ]
    types = [e["type"] for e in parsed]
    text_deltas = [e["delta"] for e in parsed if e["type"] == "text-delta"]

    # Top-level model text comes through
    assert "working" in "".join(text_deltas)
    # Subagent's LLM tokens do NOT leak
    assert "thinking" not in "".join(text_deltas)
    # Subagent's tool events flow up
    assert "tool-input-start" in types
    assert "tool-input-available" in types
    assert "tool-output-available" in types
    avail = [e for e in parsed if e["type"] == "tool-input-available"]
    assert avail[0]["toolName"] == "web_fetch"


@pytest.mark.asyncio
async def test_dispatcher_links_subagent_inner_tools_via_provider_metadata():
    """When a top-level `task` tool is called and a subagent dispatches inner
    tools, those inner events carry providerMetadata.subagent.parentToolCallId
    pointing back at the dispatcher's tool_call_id."""
    from app.streaming import stream_chat

    items = [
        # Top level: model dispatches `task`
        (
            (),
            (
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "task_1",
                            "name": "task",
                            "args": {
                                "subagent_type": "research-agent",
                                "description": "Research X",
                            },
                        }
                    ],
                ),
                {"langgraph_node": "model"},
            ),
        ),
        # Subagent: inner web_fetch
        (
            ("subagent:research-agent",),
            (
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "inner_1",
                            "name": "web_fetch",
                            "args": {"url": "https://x"},
                        }
                    ],
                ),
                {"langgraph_node": "model"},
            ),
        ),
        (
            ("subagent:research-agent",),
            (
                ToolMessage(content="page text", tool_call_id="inner_1", name="web_fetch"),
                {"langgraph_node": "tools"},
            ),
        ),
        # Top level: subagent returns
        (
            (),
            (
                ToolMessage(content="research result", tool_call_id="task_1", name="task"),
                {"langgraph_node": "tools"},
            ),
        ),
    ]
    events = []
    async for line in stream_chat(
        graph=_FakeGraph(items), thread_id="t1", lc_messages=[("user", "go")]
    ):
        events.append(line)
    parsed = [
        json.loads(e.removeprefix("data: ").strip())
        for e in events
        if e.startswith("data: {")
    ]
    inner_avail = next(
        e for e in parsed
        if e["type"] == "tool-input-available" and e.get("toolName") == "web_fetch"
    )
    inner_out = next(
        e for e in parsed
        if e["type"] == "tool-output-available" and e["toolCallId"] == "inner_1"
    )
    parent_avail = next(
        e for e in parsed
        if e["type"] == "tool-input-available" and e.get("toolName") == "task"
    )
    # Parent has no providerMetadata (top level)
    assert "providerMetadata" not in parent_avail
    # Inner events carry the parent linkage
    assert (
        inner_avail["providerMetadata"]["subagent"]["parentToolCallId"] == "task_1"
    )
    assert inner_out["providerMetadata"]["subagent"]["parentToolCallId"] == "task_1"
    assert inner_avail["providerMetadata"]["subagent"]["namespace"] == [
        "subagent:research-agent"
    ]


@pytest.mark.asyncio
async def test_stream_emits_tool_events_when_only_tool_message():
    from app.streaming import stream_chat

    items = [
        (
            ToolMessage(content="42", tool_call_id="call_x", name="calc"),
            {"langgraph_node": "tools"},
        ),
    ]
    events = []
    async for line in stream_chat(
        graph=_FakeGraph(items), thread_id="t1", lc_messages=[("user", "go")]
    ):
        events.append(line)
    parsed = [
        json.loads(e.removeprefix("data: ").strip())
        for e in events
        if e.startswith("data: {")
    ]
    types = [e["type"] for e in parsed]
    assert "tool-input-start" in types
    assert "tool-input-available" in types
    assert "tool-output-available" in types
