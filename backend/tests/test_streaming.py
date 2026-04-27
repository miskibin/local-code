import json

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel


class _FakeChatWithTools(FakeListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


@pytest.mark.asyncio
async def test_sse_stream_emits_protocol_envelope_and_deltas():
    from langgraph.checkpoint.memory import InMemorySaver

    from app.graphs.main_agent import build_agent
    from app.streaming import stream_chat

    graph = build_agent(
        llm=_FakeChatWithTools(responses=["one two"]),
        tools=[],
        checkpointer=InMemorySaver(),
    )
    events = []
    async for line in stream_chat(graph=graph, thread_id="t1", lc_messages=[("user", "go")]):
        events.append(line)

    parsed = [
        json.loads(e.removeprefix("data: ").strip()) for e in events if e.startswith("data: {")
    ]
    types = [e["type"] for e in parsed]
    assert types[0] == "start"
    assert "text-start" in types
    assert "text-delta" in types
    assert "text-end" in types
    assert types[-1] == "finish"
    assert events[-1] == "data: [DONE]\n\n"
    delta_text = "".join(e["delta"] for e in parsed if e["type"] == "text-delta")
    assert delta_text == "one two"
