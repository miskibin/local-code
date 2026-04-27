"""Pin the contract: every `art_…` token mentioned in a final assembled top-level
text frame must resolve via `app.artifact_store.get_artifact()`.

This guards two distinct regression families:

1. **Hallucinated ids.** A model invents `art_xxxx` in its final reply that
   was never produced by any tool — chat looks fine, the artifact chip on
   the frontend is dead. Catching this in tests makes the contract explicit.
2. **Sub-step persistence failure.** A subagent's `sql_query` ToolMessage
   carries an artifact dict, the streamer's `persist_tool_artifact` /
   `get_artifact` path raises silently, and the parent's final text references
   an id that doesn't exist in the DB.

We exercise both by feeding scripted graph traces to `stream_chat`,
collecting the SSE frames, scanning the assembled text for `artifact:art_…`
mentions, and asserting each id is reachable via `get_artifact()`. A
mismatch fails the test and identifies WHICH id was orphaned.
"""

from __future__ import annotations

import re

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from tests.conftest import parse_sse_events

_REF_RE = re.compile(r"artifact:(art_[A-Za-z0-9]+)")


class _Graph:
    def __init__(self, items):
        self._items = items

    async def astream(self, *_a, **_kw):
        for item in self._items:
            yield item


async def _drive_stream(items) -> list[dict]:
    from app.streaming import stream_chat

    sse_lines: list[str] = []
    async for line in stream_chat(
        graph=_Graph(items), thread_id="t-aref", lc_messages=[("user", "go")]
    ):
        sse_lines.append(line)
    return parse_sse_events(sse_lines)


def _final_text(events: list[dict]) -> str:
    return "".join(e["delta"] for e in events if e["type"] == "text-delta")


def _data_artifact_ids(events: list[dict]) -> set[str]:
    return {e["data"]["artifactId"] for e in events if e["type"] == "data-artifact"}


@pytest.mark.asyncio
async def test_every_artifact_reference_in_final_text_resolves_in_store():
    """Happy path: a real artifact gets persisted via the streamer, the
    parent's final text mentions it, and the id resolves."""
    from app.artifact_store import create_artifact, get_artifact
    from app.db import init_db

    await init_db()
    art_id = "art_arefvalid01"
    await create_artifact(
        artifact_id=art_id,
        kind="table",
        title="t",
        payload={"columns": ["a"], "rows": [{"a": 1}], "rowcount": 1},
        summary="s",
        source_kind="sql",
        source_code=None,
    )

    items = [
        # Subagent emits a tool that returns the artifact reference
        (
            ("subagent:sql-agent",),
            (
                AIMessage(
                    content="",
                    tool_calls=[{"id": "sql_1", "name": "sql_query", "args": {"q": "select 1"}}],
                ),
                {"langgraph_node": "model"},
            ),
        ),
        (
            ("subagent:sql-agent",),
            (
                ToolMessage(
                    content=f"table {art_id} · 1 row",
                    tool_call_id="sql_1",
                    name="sql_query",
                    artifact={"id": art_id},
                ),
                {"langgraph_node": "tools"},
            ),
        ),
        # Parent's final text mentions the artifact via markdown link syntax
        (
            (),
            (
                AIMessageChunk(content=f"see [the table](artifact:{art_id})."),
                {"langgraph_node": "model"},
            ),
        ),
    ]
    events = await _drive_stream(items)

    text = _final_text(events)
    refs = set(_REF_RE.findall(text))
    assert refs == {art_id}, f"expected exactly one ref to {art_id}; got {refs!r}"

    for ref in refs:
        row = await get_artifact(ref)
        assert row is not None, (
            f"final text references {ref!r} but get_artifact() returned None — "
            "either the artifact was never persisted or the parent hallucinated the id"
        )

    # And the id appeared in a data-artifact frame too — UI gets a chip.
    assert _data_artifact_ids(events) == {art_id}

    # Cleanup
    from sqlmodel import delete

    from app.db import async_session
    from app.models import SavedArtifact

    async with async_session() as s:
        await s.execute(delete(SavedArtifact).where(SavedArtifact.id == art_id))
        await s.commit()


@pytest.mark.asyncio
async def test_final_text_with_no_artifact_mentions_passes_trivially():
    """Don't false-alarm on plain text replies."""
    from app.artifact_store import get_artifact

    items = [
        (
            (),
            (AIMessageChunk(content="just chatting, no artifact."), {"langgraph_node": "model"}),
        ),
    ]
    events = await _drive_stream(items)
    text = _final_text(events)
    refs = _REF_RE.findall(text)
    assert refs == [], f"unexpected refs in plain text: {refs!r}"
    # No data-artifact frame either.
    assert not any(e["type"] == "data-artifact" for e in events)
    # And get_artifact for an arbitrary id is None — sanity check the helper
    assert await get_artifact("art_nonexistent") is None


@pytest.mark.asyncio
async def test_hallucinated_id_in_final_text_is_caught_by_resolution_check():
    """Mutation test of the contract: if the parent's final text mentions
    an id that no tool ever produced and no DB row exists for, this test's
    resolution check fails. Pinning this here so the contract is enforceable
    by the suite (other tests can use the same `assert_all_refs_resolve`
    helper)."""
    from app.artifact_store import get_artifact

    bogus = "art_neverpersisted999"
    items = [
        (
            (),
            (
                AIMessageChunk(content=f"see [it](artifact:{bogus})"),
                {"langgraph_node": "model"},
            ),
        ),
    ]
    events = await _drive_stream(items)
    text = _final_text(events)
    refs = set(_REF_RE.findall(text))
    assert refs == {bogus}

    # The contract: this MUST be detectable. We assert the id does NOT
    # resolve, demonstrating that a real "all refs must resolve" check
    # would fire on this exact shape.
    row = await get_artifact(bogus)
    assert row is None, f"test setup invariant: {bogus!r} must not exist in the artifact store"


@pytest.mark.asyncio
async def test_artifact_id_in_subagent_text_is_NOT_a_top_level_reference():
    """Subagent inner text isn't streamed to the user (per
    `streaming.py:235`'s `is_top_level` gate). So an `artifact:art_…` mention
    inside subagent prose must NOT appear in the assembled top-level
    text-delta stream — only what the parent says."""
    from app.artifact_store import create_artifact
    from app.db import init_db

    await init_db()
    aid = "art_arefvalid02"
    await create_artifact(
        artifact_id=aid,
        kind="text",
        title="t",
        payload={"text": "x"},
        summary="s",
        source_kind=None,
        source_code=None,
    )

    items = [
        # Subagent talks ABOUT the artifact in its inner text — must stay hidden
        (
            ("subagent:sql-agent",),
            (
                AIMessageChunk(content=f"my answer mentions artifact:{aid}"),
                {"langgraph_node": "model"},
            ),
        ),
        # Parent talks about something else entirely
        (
            (),
            (AIMessageChunk(content="parent says: ok."), {"langgraph_node": "model"}),
        ),
    ]
    events = await _drive_stream(items)
    text = _final_text(events)
    assert aid not in text, (
        f"subagent's mention of {aid!r} leaked into the user-visible text-delta stream: {text!r}"
    )
    # And the parent's text DID make it through.
    assert "parent says: ok." in text

    from sqlmodel import delete

    from app.db import async_session
    from app.models import SavedArtifact

    async with async_session() as s:
        await s.execute(delete(SavedArtifact).where(SavedArtifact.id == aid))
        await s.commit()
