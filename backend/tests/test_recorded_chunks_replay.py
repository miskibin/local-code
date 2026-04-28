"""Canary test: load every recorded JSONL fixture, hydrate the records into
real `AIMessageChunk` instances, and pipe them through `app.streaming.stream_chat`
against a no-op graph stub.

Catches:
  * Schema drift — `RecordedChunk.model_validate` fails if a stored fixture has
    a top-level field outside the shadow schema (i.e. the fixture was captured
    on a newer LangChain than the schema currently models).
  * Behavior drift — the streamer must produce the documented invariants for
    every recorded shape: no `skipped_events`, text fixtures yield non-empty
    `text-delta`, tool fixtures yield `tool-input-start` + `tool-input-available`.

This test never makes a network call. Fixtures are captured offline via
`backend/tests/fixtures/record.py` and committed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk

from tests.conftest import TEST_OWNER_ID
from tests.fixtures.schema import FixtureFile, RecordedChunk

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "recorded"


def _all_fixture_files() -> list[Path]:
    return sorted(FIXTURE_ROOT.rglob("*.jsonl"))


def _load_fixture(path: Path) -> tuple[FixtureFile, list[RecordedChunk]]:
    lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
    assert lines, f"empty fixture file: {path}"
    meta = FixtureFile.model_validate_json(lines[0])
    chunks = [RecordedChunk.model_validate_json(ln) for ln in lines[1:]]
    return meta, chunks


def _hydrate(rec: RecordedChunk):
    """Reconstruct a LangChain message from a recorded chunk.

    `content`, `tool_call_chunks`, `tool_calls`, `response_metadata`, and
    `usage_metadata` are the only fields the streamer reads — passing them
    through verbatim is sufficient.
    """
    content: object
    if isinstance(rec.content, str):
        content = rec.content
    else:
        content = [b.model_dump(exclude_none=True) for b in rec.content]
    rmd = rec.response_metadata.model_dump(exclude_none=True)
    umd = rec.usage_metadata.model_dump(exclude_none=True) if rec.usage_metadata else None
    tool_calls = [t.model_dump(exclude_none=True) for t in rec.tool_calls]
    tool_call_chunks = [t.model_dump(exclude_none=True) for t in rec.tool_call_chunks]
    if rec.kind == "AIMessageChunk":
        # AIMessageChunk accepts both `tool_calls` and `tool_call_chunks`; the
        # final terminal chunk in a tool-calling stream typically carries
        # `tool_calls` populated (no chunks), so we pass both through to
        # preserve the captured shape verbatim.
        return AIMessageChunk(
            content=content,
            tool_call_chunks=tool_call_chunks,
            tool_calls=tool_calls,
            response_metadata=rmd,
            usage_metadata=umd,
        )
    if rec.kind == "AIMessage":
        return AIMessage(
            content=content,
            tool_calls=tool_calls,
            response_metadata=rmd,
            usage_metadata=umd,
        )
    if rec.kind == "ToolMessage":
        # ToolMessage requires `tool_call_id`, but the current shadow schema
        # doesn't model that field. Add it to schema.RecordedChunk and wire
        # hydration here when the first ToolMessage fixture is committed.
        raise NotImplementedError(
            "ToolMessage replay isn't wired yet — extend the schema and "
            "hydration when the first ToolMessage fixture is committed"
        )
    raise ValueError(f"unsupported kind {rec.kind!r}")


class _ReplayGraph:
    def __init__(self, items):
        self._items = items

    async def astream(self, *_args, **_kwargs):
        for item in self._items:
            yield item


def test_shadow_schema_rejects_unknown_top_level_field():
    """The whole point of `extra="forbid"` is that a new upstream field on
    `AIMessageChunk` (or its sub-shapes) makes a recorded fixture fail
    validation rather than silently flow through. Pin that behavior here so
    a future relaxation of the schema is a deliberate edit, not a slip."""
    base = {
        "kind": "AIMessageChunk",
        "content": "hi",
        "tool_call_chunks": [],
        "tool_calls": [],
        "response_metadata": {},
        "usage_metadata": None,
    }
    RecordedChunk.model_validate(base)  # sanity

    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RecordedChunk.model_validate({**base, "mystery_new_field": "oops"})

    drifted_tcc = {
        **base,
        "content": "",
        "tool_call_chunks": [{"id": "x", "name": "y", "args": "z", "mystery": "oops"}],
    }
    with pytest.raises(ValidationError):
        RecordedChunk.model_validate(drifted_tcc)


def test_fixture_directory_has_at_least_one_fixture():
    """Don't let the suite go silently green if all fixtures get deleted."""
    files = _all_fixture_files()
    assert files, (
        f"no recorded fixtures found under {FIXTURE_ROOT}; "
        "the canary suite is meaningless without seeds"
    )


@pytest.mark.parametrize(
    "fixture_path", _all_fixture_files(), ids=lambda p: p.relative_to(FIXTURE_ROOT).as_posix()
)
def test_fixture_validates_against_shadow_schema(fixture_path):
    """If a fixture file ever introduces an unknown top-level field, this
    fails — forcing a deliberate schema update rather than silent drift."""
    meta, chunks = _load_fixture(fixture_path)
    assert chunks, f"fixture {fixture_path.name} has metadata but no chunks"
    # Round-trip serialization confirms the model is fully closed under JSON.
    for c in chunks:
        roundtrip = RecordedChunk.model_validate_json(c.model_dump_json())
        assert roundtrip == c, f"round-trip mismatch in {fixture_path}: {c!r} vs {roundtrip!r}"
    assert meta.provider in fixture_path.parts, (
        f"fixture meta says provider={meta.provider!r} but file lives at "
        f"{fixture_path} — keep them aligned so directory layout is browsable"
    )


@pytest.mark.parametrize(
    "fixture_path", _all_fixture_files(), ids=lambda p: p.relative_to(FIXTURE_ROOT).as_posix()
)
@pytest.mark.asyncio
async def test_fixture_replays_through_streamer_without_drops(fixture_path):
    """Hydrate fixture chunks, pipe through `stream_chat`, and assert the
    streamer emits the expected event categories with no drops.

    A regression that breaks shape handling (e.g. forgets to flatten
    list[dict] content) shows up here as missing `text-delta` events for
    text fixtures, or as a non-zero `skipped_events` counter in the
    end-of-stream log.
    """
    from app import streaming as streaming_mod
    from app.streaming import stream_chat

    meta, chunks = _load_fixture(fixture_path)
    items = [((), (_hydrate(c), {"langgraph_node": "model"})) for c in chunks]
    end_log_lines: list[str] = []
    orig_info = streaming_mod.logger.info

    def grab(msg, *a, **kw):
        end_log_lines.append(str(msg))
        return orig_info(msg, *a, **kw)

    streaming_mod.logger.info = grab
    try:
        events: list[dict] = []
        async for line in stream_chat(
            graph=_ReplayGraph(items),
            thread_id=f"fx-{fixture_path.stem}",
            lc_messages=[("user", "go")],
            owner_id=TEST_OWNER_ID,
        ):
            if line.startswith("data: {"):
                events.append(json.loads(line.removeprefix("data: ").strip()))
    finally:
        streaming_mod.logger.info = orig_info

    types = {e["type"] for e in events}
    deltas = [e["delta"] for e in events if e["type"] == "text-delta"]
    tool_starts = [e for e in events if e["type"] == "tool-input-start"]
    tool_avail = [e for e in events if e["type"] == "tool-input-available"]

    if meta.expected_text_nonempty:
        assert deltas, (
            f"{fixture_path.name}: provider={meta.provider} expected text output "
            f"but no text-delta emitted; types={types}"
        )
        # Every delta must be a string per Vercel AI SDK 6 schema.
        assert all(isinstance(d, str) for d in deltas)
        assert "".join(deltas), f"{fixture_path.name}: deltas joined to empty string"

    # If any chunk has tool_call_chunks or tool_calls, the streamer must emit
    # tool-input-start and tool-input-available — otherwise the UI sees no
    # tool card.
    has_tool_signal = any(c.tool_call_chunks or c.tool_calls for c in chunks)
    if has_tool_signal:
        assert tool_starts, (
            f"{fixture_path.name}: chunks contain tool_call signals but the "
            f"streamer never emitted a tool-input-start; events={events!r}"
        )
        assert tool_avail, (
            f"{fixture_path.name}: chunks contain tool_call signals but the "
            f"streamer never emitted a tool-input-available; events={events!r}"
        )

    # `skipped_events` in the end-of-stream log must be zero — a non-zero
    # value means the streamer received an event shape it didn't recognize,
    # i.e. our fixture replay wrapped events in a way the streamer couldn't
    # parse, OR a chunk shape changed.
    end_line = next(
        (m for m in end_log_lines if f"stream end thread=fx-{fixture_path.stem}" in m),
        "",
    )
    assert "'skipped_events': 0" in end_line, (
        f"{fixture_path.name}: streamer skipped events during replay — end log: {end_line!r}"
    )
