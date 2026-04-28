"""Golden-path integration test for `POST /chat`.

Drives the full FastAPI route — schema validation, agent build, streaming
assembly, artifact persistence — with a deterministic fake graph that
mimics the canonical user-facing flow:

    user prompt
        → top-level text intro
        → top-level `task` dispatcher tool call
            → subagent `sql_query` tool call (namespaced)
            → subagent `ToolMessage` carrying a real artifact tuple
            → subagent final text
        → top-level `task` `ToolMessage` return
        → top-level final text mentioning `[label](artifact:art_…)`

Asserts at the **structural** level — event-type ordering and required
field membership — rather than byte-equal SSE payloads. That way cosmetic
SDK frame additions (new optional fields, reordered keys) don't break the
test, but a real regression in any layer does:

  * Streaming layer drops/renames an event type → ordering check fails.
  * Subagent nesting breaks → child events miss `parentToolCallId`.
  * Artifact persistence fails → `data-artifact` frame missing.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from tests.conftest import parse_sse_events


class _FakeChatWithTools(FakeListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


class _ScriptedGraph:
    """A stand-in for the compiled langgraph agent. Yields a fixed sequence
    of `(namespace, (chunk, meta))` tuples — the same shape `stream_chat`
    consumes from the real `graph.astream(stream_mode="messages",
    subgraphs=True)`."""

    def __init__(self, items):
        self._items = items

    async def astream(self, *_args, **_kwargs):
        for item in self._items:
            yield item


def _build_canonical_event_sequence(artifact_id: str):
    """The full happy-path event stream the streamer should translate into
    a complete SSE flow.

    Mirrors the contract documented in CLAUDE.md and exercised in
    `test_streaming_tools.py::test_dispatcher_links_subagent_inner_tools_via_provider_metadata`.
    """
    return [
        # Parent: short text intro
        (
            (),
            (
                AIMessageChunk(content="Looking up customer revenue. "),
                {"langgraph_node": "model"},
            ),
        ),
        # Parent: dispatch via task tool
        (
            (),
            (
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "task_call_1",
                            "name": "task",
                            "args": {
                                "subagent_type": "sql-agent",
                                "description": "top customers",
                            },
                        }
                    ],
                ),
                {"langgraph_node": "model"},
            ),
        ),
        # Subagent: invoke sql_query
        (
            ("subagent:sql-agent",),
            (
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "sql_call_1",
                            "name": "sql_query",
                            "args": {
                                "query": "SELECT FirstName, LastName, SUM(Total) AS Spend FROM Customer JOIN Invoice USING (CustomerId) GROUP BY 1,2 LIMIT 5"
                            },
                        }
                    ],
                ),
                {"langgraph_node": "model"},
            ),
        ),
        # Subagent: tool returns artifact tuple (langchain content_and_artifact shape)
        (
            ("subagent:sql-agent",),
            (
                ToolMessage(
                    content=f"table {artifact_id} · 5 rows · cols=FirstName,LastName,Spend",
                    tool_call_id="sql_call_1",
                    name="sql_query",
                    artifact={"id": artifact_id},  # streamer uses id->get_artifact
                ),
                {"langgraph_node": "tools"},
            ),
        ),
        # Subagent: final text (matches sql-agent system prompt's exit format)
        (
            ("subagent:sql-agent",),
            (
                AIMessageChunk(
                    content=(
                        f"Top 5 customers by spend.\n"
                        f"artifact_id={artifact_id}; columns=FirstName,LastName,Spend"
                    ),
                ),
                {"langgraph_node": "model"},
            ),
        ),
        # Top level: subagent returns up the stack via the `task` ToolMessage
        (
            (),
            (
                ToolMessage(
                    content="subagent reply",
                    tool_call_id="task_call_1",
                    name="task",
                ),
                {"langgraph_node": "tools"},
            ),
        ),
        # Top level: final synthesis mentioning the artifact via markdown link
        (
            (),
            (
                AIMessageChunk(
                    content=f"Here's the [top customers table](artifact:{artifact_id}).",
                    response_metadata={"finish_reason": "STOP"},
                ),
                {"langgraph_node": "model"},
            ),
        ),
    ]


async def _seed_artifact(art_id: str) -> None:
    from app.artifact_store import create_artifact
    from tests.conftest import TEST_OWNER_ID, ensure_test_user

    await ensure_test_user()
    await create_artifact(
        owner_id=TEST_OWNER_ID,
        artifact_id=art_id,
        kind="table",
        title="Top customers",
        payload={
            "columns": ["FirstName", "LastName", "Spend"],
            "rows": [
                {"FirstName": "Alice", "LastName": "Cooper", "Spend": 50.0},
                {"FirstName": "Bob", "LastName": "Dylan", "Spend": 40.0},
            ],
            "rowcount": 2,
        },
        summary="5 rows · cols=FirstName,LastName,Spend",
        source_kind="sql",
        source_code="SELECT ...",
    )


def _build_app_with_fake_graph(monkeypatch, fake_graph) -> tuple:
    """Set up an app with the chat route's `build_agent_for_turn` patched to
    return our fake graph. Also inject a stub LLM + checkpointer per the
    pattern in `test_chat_route.py`."""
    from langgraph.checkpoint.memory import InMemorySaver

    from app.main import create_app
    from app.routes import chat as chat_route_mod

    monkeypatch.setattr(
        chat_route_mod,
        "build_agent_for_turn",
        lambda **kwargs: fake_graph,
    )

    app = create_app()
    app.state.llm_cache = {"test-model": _FakeChatWithTools(responses=["unused"])}
    app.state.checkpointer = InMemorySaver()
    return app


@pytest.mark.asyncio
async def test_chat_post_emits_canonical_v6_frame_sequence(monkeypatch):
    """End-to-end: POST /chat with a fake graph that emits the full
    user→text→task→subagent→sql→artifact→text sequence; assert SSE frames
    are present in the canonical order with the required fields and
    parent-linkage."""
    from app.db import init_db

    art_id = "art_goldenpath01"
    await init_db()
    await _seed_artifact(art_id)

    fake_graph = _ScriptedGraph(_build_canonical_event_sequence(art_id))
    app = _build_app_with_fake_graph(monkeypatch, fake_graph)

    payload = {
        "id": "thread-golden",
        "model": "test-model",
        "messages": [
            {"id": "u1", "role": "user", "parts": [{"type": "text", "text": "top customers"}]}
        ],
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers={"X-User-Email": "test@example.com"}
    ) as ac:
        r = await ac.post("/chat", json=payload)

    assert r.status_code == 200
    assert r.headers["x-vercel-ai-ui-message-stream"] == "v1"
    assert "[DONE]" in r.text

    events = parse_sse_events(r.text.splitlines())
    types = [e["type"] for e in events]

    # --- envelope frames present and in order ---
    assert types[0] == "start"
    assert types[1] == "start-step"
    assert types[-2] == "finish-step"
    assert types[-1] == "finish"

    # --- top-level text run BEFORE the dispatcher's tool-input-start ---
    first_dispatcher_idx = types.index("tool-input-start")
    text_starts_before = [
        i for i, t in enumerate(types[:first_dispatcher_idx]) if t == "text-start"
    ]
    assert text_starts_before, (
        f"expected a top-level text-start before the first tool-input-start; got types={types!r}"
    )

    # --- dispatcher (parent task) appears as TOP-LEVEL (no providerMetadata) ---
    parent_avail = next(
        e for e in events if e["type"] == "tool-input-available" and e.get("toolName") == "task"
    )
    assert "providerMetadata" not in parent_avail, (
        "dispatcher tool-input-available must be top-level (no providerMetadata)"
    )

    # --- subagent's child sql_query carries parentToolCallId == task_call_1 ---
    child_avail = next(
        e
        for e in events
        if e["type"] == "tool-input-available" and e.get("toolName") == "sql_query"
    )
    pmd = (child_avail.get("providerMetadata") or {}).get("subagent") or {}
    assert pmd.get("parentToolCallId") == "task_call_1", (
        f"sql_query parent linkage missing/wrong; providerMetadata={child_avail.get('providerMetadata')!r}"
    )
    assert pmd.get("namespace") == ["subagent:sql-agent"]

    # --- data-artifact frame emitted, with the right shape & id ---
    artifact_events = [e for e in events if e["type"] == "data-artifact"]
    assert artifact_events, f"no data-artifact frame emitted; types={types!r}"
    art = artifact_events[0]
    assert art["id"] == art_id
    assert art["data"]["artifactId"] == art_id
    assert art["data"]["kind"] == "table"
    assert art["data"]["toolCallId"] == "sql_call_1"
    # Linkage on the artifact frame too (so the UI can group it under the parent)
    assert (art["data"].get("providerMetadata") or {}).get("subagent", {}).get(
        "parentToolCallId"
    ) == "task_call_1"

    # --- ordering invariant: data-artifact comes between sql_call_1's
    #     tool-input-available and the dispatcher's tool-output-available ---
    sql_avail_idx = next(
        i
        for i, e in enumerate(events)
        if e["type"] == "tool-input-available" and e.get("toolName") == "sql_query"
    )
    artifact_idx = events.index(artifact_events[0])
    parent_done_idx = next(
        i
        for i, e in enumerate(events)
        if e["type"] == "tool-output-available" and e.get("toolCallId") == "task_call_1"
    )
    assert sql_avail_idx < artifact_idx < parent_done_idx, (
        f"event order broken: sql_avail@{sql_avail_idx} artifact@{artifact_idx} "
        f"parent_done@{parent_done_idx}; full types={types!r}"
    )

    # --- final top-level text mentions the artifact via markdown link ---
    text_deltas = [e["delta"] for e in events if e["type"] == "text-delta"]
    joined = "".join(text_deltas)
    assert f"artifact:{art_id}" in joined, (
        f"final text missing markdown artifact link; joined deltas: {joined!r}"
    )
    assert "Looking up customer revenue" in joined  # parent's intro made it through


@pytest.mark.asyncio
async def test_chat_post_with_no_subagent_dispatch_still_terminates_cleanly(monkeypatch):
    """A simpler flow (just text, no tools) must also produce a complete
    Vercel AI SDK 6 envelope. Catches a regression where the streamer's
    finalizer breaks when no tool calls happen."""
    from app.db import init_db

    items = [
        ((), (AIMessageChunk(content="hello"), {"langgraph_node": "model"})),
        (
            (),
            (
                AIMessageChunk(content=" world", response_metadata={"finish_reason": "STOP"}),
                {"langgraph_node": "model"},
            ),
        ),
    ]
    fake_graph = _ScriptedGraph(items)
    await init_db()
    app = _build_app_with_fake_graph(monkeypatch, fake_graph)

    transport = ASGITransport(app=app)
    payload = {
        "id": "thread-text-only",
        "model": "test-model",
        "messages": [{"id": "u1", "role": "user", "parts": [{"type": "text", "text": "hi"}]}],
    }
    async with AsyncClient(
        transport=transport, base_url="http://test", headers={"X-User-Email": "test@example.com"}
    ) as ac:
        r = await ac.post("/chat", json=payload)

    events = parse_sse_events(r.text.splitlines())
    types = [e["type"] for e in events]
    assert types[:2] == ["start", "start-step"]
    assert types[-2:] == ["finish-step", "finish"]
    text_deltas = [e["delta"] for e in events if e["type"] == "text-delta"]
    assert "".join(text_deltas) == "hello world"
    # No tool frames, no artifacts.
    assert "tool-input-start" not in types
    assert "data-artifact" not in types


# Don't leak the seeded artifact between tests run on a shared in-memory DB.
@pytest.fixture(autouse=True)
async def _clean_artifacts():
    yield
    from sqlmodel import delete

    from app.db import async_session
    from app.models import SavedArtifact

    async with async_session() as s:
        await s.execute(delete(SavedArtifact).where(SavedArtifact.id.like("art_goldenpath%")))
        await s.commit()
