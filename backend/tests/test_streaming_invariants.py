"""Property/parametrized tests for streaming-layer invariants.

Existing `test_streaming_tools.py` covers individual lifecycle scenarios
(consolidated AIMessage tool calls, subagent pass-through, dispatcher linkage,
finish_reason scoping, list[dict] flatten, error tool message, …). What it
*doesn't* do is sweep multiple inputs against each invariant — so a regression
that only surfaces under a specific permutation can hide.

Each test here parametrizes one invariant across several event scripts and
asserts structurally. The invariants are pinned to specific lines in
`backend/app/streaming.py` so a refactor that breaks them is traceable.
"""

from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage


class _FakeGraph:
    """Same shape as `_FakeGraph` in test_streaming_tools.py: yields prebuilt
    `(namespace, (chunk, meta))` tuples or legacy `(chunk, meta)` so the
    streamer's normalization path is exercised verbatim."""

    def __init__(self, items):
        self._items = items

    async def astream(self, *_args, **_kwargs):
        for item in self._items:
            yield item


async def _collect(items) -> list[dict]:
    from app.streaming import stream_chat

    out: list[dict] = []
    async for line in stream_chat(
        graph=_FakeGraph(items), thread_id="t-inv", lc_messages=[("user", "go")]
    ):
        if line.startswith("data: {"):
            out.append(json.loads(line.removeprefix("data: ").strip()))
    return out


# --- 1. parent-before-children ordering -------------------------------------


def _dispatcher_then_child(child_ns: tuple, child_id: str, parent_id: str = "task_1"):
    """A canonical sequence: top-level `task` dispatcher tool call, then a
    namespaced child tool call. Returns the event tuples plus the expected
    parent_id for the child."""
    return [
        (
            (),
            (
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": parent_id,
                            "name": "task",
                            "args": {"subagent_type": "x", "description": "y"},
                        }
                    ],
                ),
                {"langgraph_node": "model"},
            ),
        ),
        (
            child_ns,
            (
                AIMessage(
                    content="",
                    tool_calls=[
                        {"id": child_id, "name": "web_fetch", "args": {"url": "u"}}
                    ],
                ),
                {"langgraph_node": "model"},
            ),
        ),
        (
            child_ns,
            (
                ToolMessage(content="ok", tool_call_id=child_id, name="web_fetch"),
                {"langgraph_node": "tools"},
            ),
        ),
    ]


@pytest.mark.parametrize(
    "child_ns, child_id, parent_id",
    [
        (("subagent:a",), "child_1", "task_p1"),
        (("subagent:a", "subagent:nested"), "child_2", "task_p2"),
        (("ns_alpha",), "c_x", "t_x"),
    ],
)
@pytest.mark.asyncio
async def test_invariant_parent_dispatcher_appears_before_its_children(
    child_ns, child_id, parent_id
):
    """For every child tool event carrying `parentToolCallId=P`, a top-level
    `tool-input-start` with `toolCallId=P` must appear earlier in the stream.
    Pins `streaming.py:224-225` (parent_by_namespace set on first dispatch).
    """
    items = _dispatcher_then_child(child_ns, child_id, parent_id)
    events = await _collect(items)

    parent_indices: dict[str, int] = {}
    for i, e in enumerate(events):
        if e["type"] == "tool-input-start" and "providerMetadata" not in e:
            parent_indices[e["toolCallId"]] = i

    for i, e in enumerate(events):
        pmd = (e.get("providerMetadata") or {}).get("subagent") or {}
        parent = pmd.get("parentToolCallId")
        if parent:
            assert parent in parent_indices, (
                f"event {e!r} references parentToolCallId={parent!r} "
                f"that never appeared as a top-level tool-input-start"
            )
            assert parent_indices[parent] < i, (
                f"child event at index {i} references parent at index "
                f"{parent_indices[parent]} (parent must come first)"
            )


# --- 2. exactly one parent per namespace ------------------------------------


@pytest.mark.asyncio
async def test_invariant_namespace_locks_to_first_dispatcher_only():
    """If the parent dispatches twice (two separate `task` calls), only the
    FIRST one becomes the parent for events from a given namespace. The
    streamer must not reassign `parent_by_namespace` on a later dispatch.
    Pins `streaming.py:224` (`namespace not in parent_by_namespace` guard).
    """
    items = [
        # First dispatcher
        (
            (),
            (
                AIMessage(
                    content="",
                    tool_calls=[
                        {"id": "P1", "name": "task", "args": {"subagent_type": "a", "description": "d"}}
                    ],
                ),
                {"langgraph_node": "model"},
            ),
        ),
        # Subagent emits one inner tool — namespace locks to P1
        (
            ("subagent:a",),
            (
                AIMessage(
                    content="",
                    tool_calls=[{"id": "C1", "name": "web_fetch", "args": {}}],
                ),
                {"langgraph_node": "model"},
            ),
        ),
        (
            ("subagent:a",),
            (
                ToolMessage(content="ok", tool_call_id="C1", name="web_fetch"),
                {"langgraph_node": "tools"},
            ),
        ),
        # First dispatcher returns
        (
            (),
            (
                ToolMessage(content="r1", tool_call_id="P1", name="task"),
                {"langgraph_node": "tools"},
            ),
        ),
        # Second dispatcher with a DIFFERENT namespace
        (
            (),
            (
                AIMessage(
                    content="",
                    tool_calls=[
                        {"id": "P2", "name": "task", "args": {"subagent_type": "b", "description": "d"}}
                    ],
                ),
                {"langgraph_node": "model"},
            ),
        ),
        # Second subagent emits its inner tool from a different namespace
        (
            ("subagent:b",),
            (
                AIMessage(
                    content="",
                    tool_calls=[{"id": "C2", "name": "web_fetch", "args": {}}],
                ),
                {"langgraph_node": "model"},
            ),
        ),
        (
            ("subagent:b",),
            (
                ToolMessage(content="ok", tool_call_id="C2", name="web_fetch"),
                {"langgraph_node": "tools"},
            ),
        ),
    ]
    events = await _collect(items)
    namespace_to_parents: dict[tuple, set[str]] = {}
    for e in events:
        pmd = (e.get("providerMetadata") or {}).get("subagent") or {}
        ns = pmd.get("namespace")
        parent = pmd.get("parentToolCallId")
        if ns is None or parent is None:
            continue
        namespace_to_parents.setdefault(tuple(ns), set()).add(parent)

    for ns, parents in namespace_to_parents.items():
        assert len(parents) == 1, (
            f"namespace {ns!r} has multiple parents {parents!r}; "
            "namespace must lock to its first dispatcher"
        )
    # Sanity: both namespaces actually showed up
    assert (("subagent:a",)) in namespace_to_parents
    assert (("subagent:b",)) in namespace_to_parents
    assert namespace_to_parents[("subagent:a",)] == {"P1"}
    assert namespace_to_parents[("subagent:b",)] == {"P2"}


# --- 3. finish_reason isolated to top-level model ---------------------------


@pytest.mark.parametrize(
    "parent_finish, sub_finish, expected_visible",
    [
        ("STOP", "SAFETY", "STOP"),
        (None, "SAFETY", None),
        ("MAX_TOKENS", None, "MAX_TOKENS"),
        ("STOP", "MAX_TOKENS", "STOP"),
    ],
)
@pytest.mark.asyncio
async def test_invariant_finish_reason_only_from_top_level_model(
    parent_finish, sub_finish, expected_visible, monkeypatch
):
    """The end-of-stream diagnostic line must report the parent's finish_reason
    (or none), never a subagent's. Pins `streaming.py:199-212` (terminal
    metadata snapshot guarded by `is_top_level and node=='model'`)."""
    from app import streaming as streaming_mod

    captured: list[str] = []
    orig_info = streaming_mod.logger.info
    monkeypatch.setattr(
        streaming_mod.logger,
        "info",
        lambda msg, *a, **kw: (captured.append(str(msg)), orig_info(msg, *a, **kw))[1],
    )

    parent_md = {"finish_reason": parent_finish} if parent_finish else {}
    sub_md = {"finish_reason": sub_finish} if sub_finish else {}
    items = [
        (
            (),
            (
                AIMessageChunk(content="hi", response_metadata=parent_md),
                {"langgraph_node": "model"},
            ),
        ),
        (
            ("subagent:x",),
            (
                AIMessageChunk(content="", response_metadata=sub_md),
                {"langgraph_node": "model"},
            ),
        ),
    ]
    await _collect(items)

    end_line = next((m for m in captured if "stream end thread=t-inv" in m), "")
    if expected_visible is None:
        assert "finish_reason=None" in end_line, end_line
    else:
        assert f"finish_reason='{expected_visible}'" in end_line, end_line
    # And the subagent's reason never bleeds in (when distinct from parent's)
    if sub_finish and sub_finish != expected_visible:
        assert sub_finish not in end_line, end_line


# --- 4. empty-chunk skip across content shapes ------------------------------


@pytest.mark.parametrize(
    "content",
    [
        "",
        [],
        [{"extras": {"signature": "sig"}}],
        [{"type": "text", "text": ""}],
        [{"type": "text", "text": "", "extras": {"signature": "sig"}}],
        [{"type": "text", "text": ""}, {"type": "text", "text": ""}],
    ],
)
@pytest.mark.asyncio
async def test_invariant_empty_chunks_emit_zero_text_deltas(content):
    """Chunks whose content coerces to "" must not yield any text-delta events
    (and so must not open a text part). Pins
    `streaming.py:235` (`if is_top_level and node == "model" and chunk.content`)
    + `:237` (`if delta_text` after coercion)."""
    items = [(AIMessageChunk(content=content), {"langgraph_node": "model"})]
    events = await _collect(items)
    deltas = [e for e in events if e["type"] == "text-delta"]
    starts = [e for e in events if e["type"] == "text-start"]
    assert deltas == [], f"expected no text-delta, got {deltas!r}"
    assert starts == [], f"text-start should not open with empty content, got {starts!r}"


# --- 5. list[dict] flattening preserves text content order ------------------


@pytest.mark.parametrize(
    "content, expected",
    [
        ([{"type": "text", "text": "a"}], "a"),
        ([{"type": "text", "text": "a"}, {"type": "text", "text": "b"}], "ab"),
        (
            [
                {"type": "text", "text": "head"},
                {"extras": {"signature": "sig"}},
                {"type": "text", "text": "tail"},
            ],
            "headtail",
        ),
        (
            [
                {"type": "text", "text": "x"},
                {"type": "text", "text": "", "extras": {"signature": "s"}},
                {"type": "text", "text": "y"},
            ],
            "xy",
        ),
    ],
)
@pytest.mark.asyncio
async def test_invariant_list_dict_flatten_concat_in_order(content, expected):
    """Gemini emits content as list[dict] blocks. The streamer must flatten
    by concatenating `text` fields in source order, dropping non-text blocks.
    Pins `streaming.py:236` (delegates to `coerce_lc_content`)."""
    items = [(AIMessageChunk(content=content), {"langgraph_node": "model"})]
    events = await _collect(items)
    deltas = [e["delta"] for e in events if e["type"] == "text-delta"]
    assert all(isinstance(d, str) for d in deltas)
    assert "".join(deltas) == expected


# --- 6. tool args buffer JSON parse fallback --------------------------------


@pytest.mark.asyncio
async def test_invariant_tool_args_buffer_falls_back_to_raw_on_bad_json():
    """When the model streams tool_call args in chunks but the joined buffer
    isn't valid JSON, the streamer must still emit `tool-input-available`
    with `_raw` so the UI can present the malformed args rather than swallow
    the call. Pins `streaming.py:325` (`parsed = {"_raw": raw}`)."""
    # langchain auto-parses partial-but-recoverable JSON into `tool_calls`
    # (with `args={}` for unparseable). To force the buffer-flush path (where
    # `tool_calls` is empty so the AIMessage branch never pre-announces), use
    # a clearly malformed args payload — langchain routes it to
    # `invalid_tool_calls` instead, leaving `tool_calls=[]`.
    items = [
        (
            AIMessageChunk(
                content="",
                tool_call_chunks=[
                    {"id": "tc1", "name": "web_fetch", "args": "!!!not-json!!!"}
                ],
            ),
            {"langgraph_node": "model"},
        ),
        (
            ToolMessage(content="page", tool_call_id="tc1", name="web_fetch"),
            {"langgraph_node": "tools"},
        ),
    ]
    events = await _collect(items)
    avail = [e for e in events if e["type"] == "tool-input-available" and e["toolCallId"] == "tc1"]
    assert avail, f"no tool-input-available emitted for tc1: {events!r}"
    # The args buffer was malformed JSON, so the streamer's args-buffer-flush
    # path produces `{"_raw": "<raw-string>"}`. (If the AIMessage path beat us
    # to it, the args would be parsed by the model directly — that's a
    # different code path. We're pinning the buffer fallback here.)
    inputs = [e["input"] for e in avail]
    raw_seen = any(isinstance(x, dict) and "_raw" in x for x in inputs)
    assert raw_seen, (
        f"expected one tool-input-available with `{{'_raw': ...}}` after "
        f"malformed JSON args; got inputs={inputs!r}"
    )


# --- 7. dispatcher detection top-level only ---------------------------------


@pytest.mark.asyncio
async def test_invariant_subagent_calling_task_does_not_register_new_dispatcher():
    """If a subagent itself emits a `task` tool call (rare but possible), it
    must NOT be tracked as a new dispatcher — only top-level dispatchers
    parent inner events. Pins `streaming.py:284`
    (`if is_top_level and name in DISPATCHER_TOOLS`)."""
    items = [
        # Top-level dispatcher
        (
            (),
            (
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "TOP_TASK",
                            "name": "task",
                            "args": {"subagent_type": "a", "description": "d"},
                        }
                    ],
                ),
                {"langgraph_node": "model"},
            ),
        ),
        # Subagent emits its OWN task call
        (
            ("subagent:a",),
            (
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "INNER_TASK",
                            "name": "task",
                            "args": {"subagent_type": "b", "description": "d"},
                        }
                    ],
                ),
                {"langgraph_node": "model"},
            ),
        ),
        # Then a subagent inner non-task tool — its parent must remain TOP_TASK,
        # NOT INNER_TASK (which would be the case if subagent dispatchers were
        # tracked).
        (
            ("subagent:a",),
            (
                AIMessage(
                    content="",
                    tool_calls=[{"id": "INNER_FETCH", "name": "web_fetch", "args": {}}],
                ),
                {"langgraph_node": "model"},
            ),
        ),
        (
            ("subagent:a",),
            (
                ToolMessage(content="ok", tool_call_id="INNER_FETCH", name="web_fetch"),
                {"langgraph_node": "tools"},
            ),
        ),
    ]
    events = await _collect(items)
    fetch_events = [
        e
        for e in events
        if e["type"] in {"tool-input-available", "tool-output-available"}
        and e["toolCallId"] == "INNER_FETCH"
    ]
    assert fetch_events, "no events emitted for INNER_FETCH"
    for e in fetch_events:
        pmd = (e.get("providerMetadata") or {}).get("subagent") or {}
        assert pmd.get("parentToolCallId") == "TOP_TASK", (
            f"INNER_FETCH wrongly attributed to {pmd.get('parentToolCallId')!r} "
            f"instead of the top-level dispatcher TOP_TASK; event={e!r}"
        )


# --- 8. legacy (chunk, meta) tuple shape still works ------------------------


@pytest.mark.asyncio
async def test_invariant_legacy_no_subgraph_tuple_shape_supported():
    """`graph.astream(..., subgraphs=False)` historically yielded `(chunk,
    meta)` instead of `(namespace, (chunk, meta))`. The streamer normalizes
    both at `streaming.py:175-177`. Pin so a refactor doesn't drop legacy."""
    items = [
        (AIMessageChunk(content="hi"), {"langgraph_node": "model"}),
    ]
    events = await _collect(items)
    deltas = [e["delta"] for e in events if e["type"] == "text-delta"]
    assert deltas == ["hi"]


# --- 9. malformed payload increments skip counter (does not crash) ----------


@pytest.mark.asyncio
async def test_invariant_malformed_event_payload_increments_counter(monkeypatch):
    """An event tuple that doesn't match either expected shape is logged + the
    `skipped_events` counter increments — the stream must not crash. Pins
    `streaming.py:178-187`."""
    from app import streaming as streaming_mod

    captured: list[str] = []
    orig = streaming_mod.logger.info
    monkeypatch.setattr(
        streaming_mod.logger,
        "info",
        lambda msg, *a, **kw: (captured.append(str(msg)), orig(msg, *a, **kw))[1],
    )

    items = [
        ("garbage_payload",),
        (AIMessageChunk(content="ok"), {"langgraph_node": "model"}),
    ]
    events = await _collect(items)
    deltas = [e["delta"] for e in events if e["type"] == "text-delta"]
    assert deltas == ["ok"]  # the valid one still goes through
    end_line = next((m for m in captured if "stream end thread=t-inv" in m), "")
    assert "skipped_events" in end_line and "skipped_events': 1" in end_line.replace(
        '"', "'"
    ), end_line
