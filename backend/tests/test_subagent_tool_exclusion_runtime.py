"""Runtime regression tests for the per-subagent tool-exclusion middleware.

`test_main_agent.test_build_agent_extends_tool_exclusion_to_each_subagent` asserts
that the middleware *object* is attached to every subagent spec. That's a wiring
test: it goes green even if the middleware's filter logic is broken or if
deepagents stops calling our middleware at runtime.

These tests assert the *consequence*: the excluded built-in tool names actually
disappear from the model's bound roster at request time, both for direct
middleware invocation (unit) and through the full `build_agent` graph including
a dispatched subagent (integration).
"""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import BaseTool, tool
from pydantic import Field

from app.middleware.tool_exclusion import ToolExclusionMiddleware


@tool("safe_tool")
def _safe_tool(x: int) -> int:
    """allowed tool"""
    return x


@tool("ls")
def _ls(path: str) -> str:
    """excluded built-in stand-in"""
    return path


# --- Unit: middleware filter behavior ---------------------------------------


def _make_request_stub(tools: list[BaseTool]):
    """Minimal ModelRequest stand-in: only the fields the middleware touches.

    Avoids constructing a real `ModelRequest` (which pulls in a model,
    messages, runtime, etc. — none of which the exclusion logic reads).
    """

    class _Req:
        def __init__(self, tools_: list[BaseTool]):
            self.tools = tools_

        def override(self, *, tools):
            return _Req(tools)

    return _Req(tools)


def test_middleware_strips_excluded_tools_from_handler_view_sync():
    excluded = frozenset({"ls", "grep"})
    mw = ToolExclusionMiddleware(excluded=excluded)

    req = _make_request_stub([_ls, _safe_tool])
    seen: list[list[str]] = []

    def handler(filtered_req):
        seen.append([t.name for t in filtered_req.tools])
        return "ok"

    out = mw.wrap_model_call(req, handler)

    assert out == "ok"
    assert seen == [["safe_tool"]], (
        "middleware must remove excluded names from request.tools before "
        f"the handler runs; got {seen}"
    )


@pytest.mark.asyncio
async def test_middleware_strips_excluded_tools_from_handler_view_async():
    excluded = frozenset({"ls", "grep"})
    mw = ToolExclusionMiddleware(excluded=excluded)

    req = _make_request_stub([_ls, _safe_tool])
    seen: list[list[str]] = []

    async def handler(filtered_req):
        seen.append([t.name for t in filtered_req.tools])
        return "ok"

    out = await mw.awrap_model_call(req, handler)

    assert out == "ok"
    assert seen == [["safe_tool"]]


def test_middleware_passthrough_when_excluded_set_empty():
    """Empty exclusion set is a no-op — the original request must reach the
    handler with tools intact (covers the `if self._excluded` short-circuit
    so an accidental empty frozenset doesn't silently drop a real tool)."""
    mw = ToolExclusionMiddleware(excluded=frozenset())
    req = _make_request_stub([_ls, _safe_tool])
    seen: list[list[str]] = []

    def handler(r):
        seen.append([t.name for t in r.tools])

    mw.wrap_model_call(req, handler)
    assert seen == [["ls", "safe_tool"]]


# --- Integration: subagent's model request never sees excluded tools --------


class _ScriptedToolCaller(FakeListChatModel):
    """Chat model that returns scripted `AIMessage` objects per invocation,
    so we can deterministically force the parent to dispatch a subagent.

    `FakeListChatModel`'s `_stream` returns plain text characters and ignores
    structured outputs; we override `_generate`/`_agenerate` so the agent
    sees real `tool_calls` on the parent's first turn.
    """

    # FakeListChatModel is a pydantic BaseModel; declaring as Fields with
    # `default_factory=list` keeps each instance's state independent so tests
    # can mutate without leaking across test runs.
    bound_tool_names: list[list[str]] = Field(default_factory=list)
    scripted_messages: list[BaseMessage] = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        names = []
        for t in tools or []:
            n = getattr(t, "name", None) or getattr(t, "__name__", None)
            if isinstance(t, dict):
                n = t.get("name") or t.get("function", {}).get("name") or n
            names.append(n or str(t))
        self.bound_tool_names.append(names)
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        msg = self.scripted_messages.pop(0) if self.scripted_messages else AIMessage(content="done")
        return ChatResult(generations=[ChatGeneration(message=msg)])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


@pytest.mark.asyncio
async def test_subagent_model_never_sees_excluded_builtins_at_runtime(monkeypatch):
    """Drive a real `build_agent` graph through a top-level dispatch into a
    subagent and assert: every model invocation that the per-subagent
    `ToolExclusionMiddleware` wraps presents the handler with a tools list
    that contains NONE of `_EXCLUDED_BUILTIN_TOOLS`.

    We observe the middleware's effect by subclassing it and recording the
    post-filter list at the handler boundary (the same boundary the real
    LLM would see). This pins behavior, not wiring: a regression that drops
    the per-subagent middleware wrap in `main_agent.py:56-65` would mean
    fewer recorded instances and/or a leaked excluded name in the captured
    list — either way, the test goes red while the wiring test stays green.
    """
    from langgraph.checkpoint.memory import InMemorySaver

    from app.graphs import main_agent as main_agent_mod
    from app.graphs.main_agent import _EXCLUDED_BUILTIN_TOOLS

    captured: list[tuple[int, list[str]]] = []
    instances: list[Any] = []

    class _RecordingExclusion(ToolExclusionMiddleware):
        def __init__(self, *, excluded):
            super().__init__(excluded=excluded)
            instances.append(self)

        def wrap_model_call(self, request, handler):
            instance_id = id(self)

            def _record(req):
                captured.append((instance_id, [getattr(t, "name", str(t)) for t in req.tools]))
                return handler(req)

            return super().wrap_model_call(request, _record)

        async def awrap_model_call(self, request, handler):
            instance_id = id(self)

            async def _record(req):
                captured.append((instance_id, [getattr(t, "name", str(t)) for t in req.tools]))
                return await handler(req)

            return await super().awrap_model_call(request, _record)

    monkeypatch.setattr(main_agent_mod, "ToolExclusionMiddleware", _RecordingExclusion)

    llm = _ScriptedToolCaller(responses=["unused"])
    llm.bound_tool_names = []
    llm.scripted_messages = [
        # Parent turn 1: dispatch to subagent via the `task` tool
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "task_call_1",
                    "name": "task",
                    "args": {
                        "subagent_type": "research-agent",
                        "description": "demo dispatch",
                    },
                }
            ],
        ),
        # Subagent turn: end with a final reply (no tools)
        AIMessage(content="subagent done"),
        # Parent turn 2: synthesize final reply
        AIMessage(content="all done"),
    ]

    graph = main_agent_mod.build_agent(
        llm=llm,
        tools=[_safe_tool],
        checkpointer=InMemorySaver(),
        subagents=[
            {
                "name": "research-agent",
                "description": "research",
                "system_prompt": "be brief",
                "tools": [],
            }
        ],
    )

    await graph.ainvoke(
        {"messages": [("user", "go")]},
        config={"configurable": {"thread_id": "tex-1"}},
    )

    assert len(instances) >= 2, (
        "expected at least 2 ToolExclusionMiddleware instances "
        f"(one for parent, one per subagent); got {len(instances)}"
    )
    assert captured, (
        "the middleware's awrap_model_call was never invoked at runtime — "
        "either the parent never called the model or the middleware isn't in "
        "the runtime chain"
    )

    # Per-instance: every observed handler-view tools list must be free of
    # excluded names.
    excluded = set(_EXCLUDED_BUILTIN_TOOLS)
    leaks = [(iid, names, [n for n in names if n in excluded]) for iid, names in captured]
    leaks = [x for x in leaks if x[2]]
    assert not leaks, (
        f"excluded built-ins reached the model handler: {leaks!r}; "
        f"all captured rosters: {captured!r}"
    )

    # Also confirm we exercised more than one middleware instance at runtime
    # — meaning both the parent's and at least one subagent's middleware ran.
    distinct_instance_ids = {iid for iid, _ in captured}
    assert len(distinct_instance_ids) >= 2, (
        "expected awrap_model_call calls from >=2 distinct middleware instances "
        f"(parent + subagent); got {len(distinct_instance_ids)} from "
        f"captured={captured!r}"
    )


@pytest.mark.asyncio
async def test_general_purpose_dispatch_never_calls_a_model(monkeypatch):
    """Regression: a previous bug let the model dispatch
    `task(subagent_type="general-purpose", ...)` into a stub subagent that
    deepagents wired up with the default middleware stack
    (TodoList + Filesystem + ...), which then injected `ls`/`grep`/etc into
    the subagent's model request. The fix replaces the stub with a
    CompiledSubAgent (`runnable` key) that immediately returns a refusal
    ToolMessage — no model bind, no Filesystem tools.

    This pins the contract: dispatching to general-purpose must produce
    zero model invocations *inside* the subagent. The bound-tool roster
    therefore must remain identical to the parent's.
    """
    from langgraph.checkpoint.memory import InMemorySaver

    from app.graphs.main_agent import build_agent

    llm = _ScriptedToolCaller(responses=["unused"])
    llm.bound_tool_names = []
    llm.scripted_messages = [
        # Parent turn 1: dispatch to general-purpose (the disabled stub)
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "task_call_1",
                    "name": "task",
                    "args": {
                        "subagent_type": "general-purpose",
                        "description": "do anything",
                    },
                }
            ],
        ),
        # Parent turn 2: synthesize final reply after the refusal comes back
        AIMessage(content="acknowledged refusal"),
    ]

    graph = build_agent(
        llm=llm,
        tools=[_safe_tool],
        checkpointer=InMemorySaver(),
    )

    result = await graph.ainvoke(
        {"messages": [("user", "go")]},
        config={"configurable": {"thread_id": "gp-1"}},
    )

    # Exactly two LLM bindings occurred — both for the parent. None for the
    # subagent (since it's a `runnable` graph that bypasses the LLM).
    assert len(llm.bound_tool_names) == 2, (
        "general-purpose dispatch should not invoke any LLM inside the "
        f"subagent; got {len(llm.bound_tool_names)} model bind(s): "
        f"{llm.bound_tool_names!r}"
    )

    # Refusal text must surface as the task tool's ToolMessage so the parent
    # sees a clean signal, not an LLM-generated tangent.
    from langchain_core.messages import ToolMessage

    refusals = [
        m for m in result["messages"]
        if isinstance(m, ToolMessage) and "disabled" in (m.content or "").lower()
    ]
    assert refusals, (
        "expected a refusal ToolMessage from the disabled general-purpose "
        f"subagent; got messages={[type(m).__name__ for m in result['messages']]}"
    )


@pytest.mark.asyncio
async def test_excluded_tool_call_is_refused_at_execution_time():
    """Regression: filtering at ``bind_tools`` time only stops the model from
    *seeing* excluded tools. ``ToolNode`` still has them registered, and small
    models (gemma) routinely emit tool_calls for names they were never bound
    to (recalled from training prior). Without ``wrap_tool_call``, those
    hallucinated calls get *executed* — exactly the leak observed in
    production where ``ls``/``grep`` ran despite our model-level exclusion.

    Force a hallucinated ``ls`` call via scripted ``AIMessage.tool_calls`` and
    assert the resulting ``ToolMessage`` is a refusal (status='error', name
    'ls'), not a real ``ls`` execution.
    """
    from langchain_core.messages import ToolMessage
    from langgraph.checkpoint.memory import InMemorySaver

    from app.graphs.main_agent import build_agent

    llm = _ScriptedToolCaller(responses=["unused"])
    llm.bound_tool_names = []
    llm.scripted_messages = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "ls_call_1",
                    "name": "ls",
                    "args": {"path": "/"},
                }
            ],
        ),
        AIMessage(content="acknowledged"),
    ]

    graph = build_agent(
        llm=llm,
        tools=[_safe_tool],
        checkpointer=InMemorySaver(),
    )

    result = await graph.ainvoke(
        {"messages": [("user", "trigger ls hallucination")]},
        config={"configurable": {"thread_id": "lsh-1"}},
    )

    ls_msgs = [
        m for m in result["messages"]
        if isinstance(m, ToolMessage) and m.name == "ls"
    ]
    assert ls_msgs, (
        "expected a ToolMessage for the hallucinated `ls` call; "
        f"got messages={[type(m).__name__ for m in result['messages']]}"
    )
    refusal = ls_msgs[0]
    assert refusal.status == "error", (
        f"hallucinated `ls` should refuse with status='error', got "
        f"status={refusal.status!r} content={refusal.content!r}"
    )
    assert "not available" in (refusal.content or "").lower(), (
        f"refusal content should explain tool is unavailable; got {refusal.content!r}"
    )


def test_excluded_set_matches_documented_builtins():
    """The exclusion set is the contract between us and deepagents. If
    deepagents renames or splits a built-in (e.g. `read_file` → `fs_read`),
    our exclusion silently misses it. Pin the names here so a rename forces
    a deliberate update."""
    from app.graphs.main_agent import _EXCLUDED_BUILTIN_TOOLS

    assert (
        frozenset({"ls", "read_file", "write_file", "edit_file", "glob", "grep", "execute"})
        == _EXCLUDED_BUILTIN_TOOLS
    )
