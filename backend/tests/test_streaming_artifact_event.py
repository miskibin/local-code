import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage


class _FakeGraph:
    def __init__(self, items):
        self._items = items

    async def astream(self, *_args, **_kwargs):
        for item in self._items:
            yield item


@pytest.mark.asyncio
async def test_tool_artifact_available_emitted_when_tool_message_carries_artifact():
    from app.db import init_db
    from app.streaming import stream_chat

    await init_db()

    tm = ToolMessage(
        content="table 1 rows x 1 cols (n)",
        tool_call_id="call_a",
        name="python_exec",
        artifact={
            "kind": "table",
            "title": "Demo",
            "payload": {
                "columns": [{"key": "n", "label": "n"}],
                "rows": [{"n": 7}],
            },
            "summary": "table 1 rows x 1 cols (n)",
            "source_kind": "python",
            "source_code": "out([{'n': 7}])",
        },
    )

    items = [
        (
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call_a",
                        "name": "python_exec",
                        "args": {"code": "out([{'n': 7}])"},
                    }
                ],
            ),
            {"langgraph_node": "model"},
        ),
        (tm, {"langgraph_node": "tools"}),
    ]
    events = []
    async for line in stream_chat(
        graph=_FakeGraph(items),
        thread_id="t1",
        lc_messages=[("user", "go")],
        session_id="t1",
    ):
        events.append(line)

    parsed = [
        json.loads(e.removeprefix("data: ").strip()) for e in events if e.startswith("data: {")
    ]
    types = [e["type"] for e in parsed]
    assert "tool-output-available" in types
    assert "data-artifact" in types
    art_evt = next(e for e in parsed if e["type"] == "data-artifact")
    body = art_evt["data"]
    assert body["toolCallId"] == "call_a"
    assert body["kind"] == "table"
    assert body["title"] == "Demo"
    assert body["summary"].startswith("table 1 rows")
    assert body["artifactId"]
    assert "updatedAt" in body

    # tool-output-available must carry the SUMMARY (string), not the payload.
    out = next(e for e in parsed if e["type"] == "tool-output-available")
    assert isinstance(out["output"], str)
    assert "table 1 rows" in out["output"]


@pytest.mark.asyncio
async def test_no_artifact_event_when_tool_message_has_no_artifact():
    from app.streaming import stream_chat

    items = [
        (
            AIMessage(
                content="",
                tool_calls=[{"id": "c1", "name": "web_fetch", "args": {"url": "x"}}],
            ),
            {"langgraph_node": "model"},
        ),
        (
            ToolMessage(content="ok", tool_call_id="c1", name="web_fetch"),
            {"langgraph_node": "tools"},
        ),
    ]
    events = []
    async for line in stream_chat(graph=_FakeGraph(items), thread_id="t", lc_messages=[("u", "g")]):
        events.append(line)
    parsed = [
        json.loads(e.removeprefix("data: ").strip()) for e in events if e.startswith("data: {")
    ]
    assert "data-artifact" not in [e["type"] for e in parsed]
