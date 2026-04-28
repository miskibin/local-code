import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from app.models import SavedArtifact, SavedTask
from app.tasks.runner import run_task
from app.tasks.schemas import TaskDTO, TaskStep, TaskVariable
from app.tasks.storage import upsert_task
from tests.conftest import TEST_OWNER_ID, parse_sse_events, reset_task_tables


@tool
def echo_tool(text: str) -> str:
    """Return the supplied text unchanged."""
    return f"echo:{text}"


async def _collect(stream) -> list[dict]:
    return parse_sse_events([line async for line in stream])


async def _persist_task(*, steps: list[TaskStep], variables: list[TaskVariable]):
    dto = TaskDTO(
        id="tsk_runtest1234",
        title="Runner test",
        variables=variables,
        steps=steps,
    )
    return await upsert_task(dto, TEST_OWNER_ID)


@pytest.mark.asyncio
async def test_runner_executes_tool_step_with_substitution(monkeypatch, stub_state):
    await reset_task_tables(SavedTask, SavedArtifact)

    monkeypatch.setattr("app.tasks.runner.tool_registry.discover_tools", lambda: [echo_tool])

    task = await _persist_task(
        steps=[
            TaskStep(
                id="s1",
                kind="tool",
                title="Echo",
                tool="echo_tool",
                args_template={"text": "hello {{var.who}}"},
                output_name="said",
                output_kind="text",
            )
        ],
        variables=[TaskVariable(name="who", type="string", label="Who")],
    )

    events = await _collect(
        run_task(
            task,
            {"who": "world"},
            state=stub_state,
            session_id="run-sess-1",
            owner_id=TEST_OWNER_ID,
            llm=FakeListChatModel(responses=["unused"]),
        )
    )
    types = [e["type"] for e in events]
    assert "tool-input-start" in types
    assert "tool-input-available" in types
    assert "tool-output-available" in types
    input_evt = next(e for e in events if e["type"] == "tool-input-available")
    assert input_evt["toolName"] == "echo_tool"
    assert input_evt["input"] == {"text": "hello world"}
    assert input_evt["providerMetadata"]["task"] == {
        "stepId": "s1",
        "title": "Echo",
        "kind": "tool",
    }
    output_evt = next(e for e in events if e["type"] == "tool-output-available")
    assert output_evt["output"] == "echo:hello world"
    assert "tool-output-error" not in types


@pytest.mark.asyncio
async def test_runner_runs_prompt_step_via_llm(stub_state):
    await reset_task_tables(SavedTask)

    task = await _persist_task(
        steps=[
            TaskStep(
                id="p1",
                kind="prompt",
                title="Summarise",
                prompt="Summarise {{var.topic}} in one sentence.",
                output_name="summary",
                output_kind="text",
            )
        ],
        variables=[TaskVariable(name="topic", type="string", label="Topic")],
    )
    events = await _collect(
        run_task(
            task,
            {"topic": "indices"},
            state=stub_state,
            session_id="run-sess-prompt",
            owner_id=TEST_OWNER_ID,
            llm=FakeListChatModel(responses=["Indices speed up reads."]),
        )
    )
    types = [e["type"] for e in events]
    assert "tool-input-available" not in types
    assert "tool-output-available" not in types
    deltas = "".join(e["delta"] for e in events if e["type"] == "text-delta")
    assert "Summarise" in deltas
    assert "Indices speed up reads." in deltas


@pytest.mark.asyncio
async def test_runner_subagent_step_exposes_artifact_id_for_chaining(monkeypatch, stub_state):
    await reset_task_tables(SavedTask)

    @tool
    def chart_stub(artifact_id: str) -> str:
        """Pretend to chart an artifact."""
        return f"plotted {artifact_id}"

    monkeypatch.setattr(
        "app.tasks.runner.tool_registry.discover_tools",
        lambda: [chart_stub],
    )

    task = await _persist_task(
        steps=[
            TaskStep(
                id="s1",
                kind="subagent",
                title="Pretend subagent",
                subagent="sql-agent",
                prompt="produce summary",
                output_name="summary",
                output_kind="text",
            ),
            TaskStep(
                id="s2",
                kind="tool",
                title="Plot",
                tool="chart_stub",
                args_template={"artifact_id": "{{s1.artifact_id}}"},
                output_name="chart",
                output_kind="chart",
            ),
        ],
        variables=[],
    )
    # Replace the prompt step output with one that includes the SQL contract
    # trailer so we can exercise artifact_id parsing for downstream steps.
    fake_response = "Top spend computed.\nartifact_id=art_deadbeef0000; columns=A,B"
    events = await _collect(
        run_task(
            task,
            {},
            state=stub_state,
            session_id="run-chain",
            owner_id=TEST_OWNER_ID,
            llm=FakeListChatModel(responses=[fake_response]),
        )
    )
    types = [e["type"] for e in events]
    assert "tool-output-error" not in types
    s2_output = next(
        e for e in events if e["type"] == "tool-output-available" and e["toolCallId"] == "s2"
    )
    assert "art_deadbeef0000" in str(s2_output["output"])


@pytest.mark.asyncio
async def test_runner_halts_on_missing_variable(monkeypatch, stub_state):
    await reset_task_tables(SavedTask)

    monkeypatch.setattr("app.tasks.runner.tool_registry.discover_tools", lambda: [echo_tool])

    task = await _persist_task(
        steps=[
            TaskStep(
                id="s1",
                kind="tool",
                title="Echo",
                tool="echo_tool",
                args_template={"text": "{{var.missing}}"},
                output_name="said",
                output_kind="text",
            ),
            TaskStep(
                id="s2",
                kind="tool",
                title="Should not run",
                tool="echo_tool",
                args_template={"text": "x"},
                output_name="said",
                output_kind="text",
            ),
        ],
        variables=[],
    )

    events = await _collect(
        run_task(
            task,
            {},
            state=stub_state,
            session_id="run-sess-fail",
            owner_id=TEST_OWNER_ID,
            llm=FakeListChatModel(responses=["x"]),
        )
    )
    errors = [e for e in events if e["type"] == "tool-output-error"]
    assert len(errors) == 1 and errors[0]["toolCallId"] == "s1"
    started = [e for e in events if e["type"] == "tool-input-start"]
    assert all(e["toolCallId"] != "s2" for e in started)


@pytest.mark.asyncio
async def test_runner_code_step_emits_python_exec_event_shape(monkeypatch, stub_state):
    """A kind=code step must emit toolName=python_exec with input={code: ...},
    so the same per-tool renderer that handles chat python_exec calls picks it
    up automatically."""
    await reset_task_tables(SavedTask, SavedArtifact)

    monkeypatch.setattr("app.tasks.runner.tool_registry.discover_tools", list)

    task = await _persist_task(
        steps=[
            TaskStep(
                id="c1",
                kind="code",
                title="Compute",
                code="out([{'n': {{var.top_n}} }])",
                output_name="rows",
                output_kind="rows",
            )
        ],
        variables=[TaskVariable(name="top_n", type="number", label="N", default=3)],
    )
    events = await _collect(
        run_task(
            task,
            {"top_n": 3},
            state=stub_state,
            session_id="run-sess-code",
            owner_id=TEST_OWNER_ID,
            llm=FakeListChatModel(responses=["unused"]),
        )
    )
    input_evt = next(
        e for e in events if e["type"] == "tool-input-available" and e["toolCallId"] == "c1"
    )
    assert input_evt["toolName"] == "python_exec"
    assert "code" in input_evt["input"]
    assert "out(" in input_evt["input"]["code"]
    assert input_evt["providerMetadata"]["task"]["title"] == "Compute"


@pytest.mark.asyncio
async def test_runner_subagent_inner_tool_carries_parent_link(monkeypatch, stub_state):
    """Inner tool calls inside a subagent step must carry
    providerMetadata.subagent.parentToolCallId == step.id so the frontend's
    SubagentStep grouping pulls them under the dispatcher card."""
    await reset_task_tables(SavedTask)

    @tool
    def sql_query(query: str) -> str:
        """Run a stub SQL query."""
        return "table art_inner1234 · 2 rows"

    monkeypatch.setattr(
        "app.tasks.runner.tool_registry.discover_tools",
        lambda: [sql_query],
    )

    class _ToolCallingLLM(FakeListChatModel):
        """First response calls sql_query; second is a plain text reply."""

        def bind_tools(self, tools, **kwargs):
            return self

        async def ainvoke(self, messages, *args, **kwargs):
            from langchain_core.messages import AIMessage

            if not getattr(self, "_step", 0):
                self._step = 1
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "tc_inner_1",
                            "name": "sql_query",
                            "args": {"query": "SELECT 1"},
                        }
                    ],
                )
            return AIMessage(content="done.\nartifact_id=art_inner1234; columns=A")

    task = await _persist_task(
        steps=[
            TaskStep(
                id="sa1",
                kind="subagent",
                title="Run SQL",
                subagent="sql-agent",
                prompt="produce summary",
                output_name="summary",
                output_kind="text",
            )
        ],
        variables=[],
    )
    events = await _collect(
        run_task(
            task,
            {},
            state=stub_state,
            session_id="run-inner",
            owner_id=TEST_OWNER_ID,
            llm=_ToolCallingLLM(responses=["unused"]),
        )
    )
    inner_input = next(
        e for e in events if e["type"] == "tool-input-available" and e["toolName"] == "sql_query"
    )
    sub_md = inner_input["providerMetadata"]["subagent"]
    assert sub_md["parentToolCallId"] == "sa1"
    assert sub_md["namespace"] == ["task:sa1"]

    dispatcher_input = next(
        e for e in events if e["type"] == "tool-input-available" and e["toolCallId"] == "sa1"
    )
    assert dispatcher_input["toolName"] == "task"
    assert dispatcher_input["input"]["subagent_type"] == "sql-agent"


@pytest.mark.asyncio
async def test_runner_tool_step_exposes_artifact_id_for_chaining(monkeypatch, stub_state):
    """A content_and_artifact tool step must surface artifact_id so downstream
    {{stepId.artifact_id}} substitution resolves — the generator now produces
    direct sql_query tool steps, so this is the chain that must hold."""
    await reset_task_tables(SavedTask, SavedArtifact)

    from langchain_core.tools import tool as lc_tool

    @lc_tool(response_format="content_and_artifact")
    async def fake_sql(sql: str) -> tuple[str, dict]:
        """Fake SQL that returns a table artifact."""
        return ("art_fake5678 · sql 1 row", {"id": "art_fake5678", "kind": "table"})

    @lc_tool
    def echo_id(artifact_id: str) -> str:
        """Echo the supplied artifact_id."""
        return f"got:{artifact_id}"

    monkeypatch.setattr(
        "app.tasks.runner.tool_registry.discover_tools",
        lambda: [fake_sql, echo_id],
    )
    task = await _persist_task(
        steps=[
            TaskStep(
                id="s1",
                kind="tool",
                title="SQL",
                tool="fake_sql",
                args_template={"sql": "SELECT 1"},
                output_name="rows",
                output_kind="rows",
            ),
            TaskStep(
                id="s2",
                kind="tool",
                title="Plot",
                tool="echo_id",
                args_template={"artifact_id": "{{s1.artifact_id}}"},
                output_name="echoed",
                output_kind="text",
            ),
        ],
        variables=[],
    )
    events = await _collect(
        run_task(
            task,
            {},
            state=stub_state,
            session_id="run-tool-chain",
            owner_id=TEST_OWNER_ID,
            llm=FakeListChatModel(responses=["unused"]),
        )
    )
    assert not [e for e in events if e["type"] == "tool-output-error"], events
    s2 = next(e for e in events if e["type"] == "tool-input-available" and e["toolCallId"] == "s2")
    assert s2["input"]["artifact_id"] == "art_fake5678"


@pytest.mark.asyncio
async def test_runner_appends_lc_messages_for_persistence(monkeypatch, stub_state):
    """run_task fills caller-supplied lc_messages with Human/AI/Tool LC messages
    so the chat route can persist them to the LangGraph checkpointer."""
    await reset_task_tables(SavedTask, SavedArtifact)

    monkeypatch.setattr("app.tasks.runner.tool_registry.discover_tools", lambda: [echo_tool])

    task = await _persist_task(
        steps=[
            TaskStep(
                id="s1",
                kind="tool",
                title="Echo",
                tool="echo_tool",
                args_template={"text": "hi {{var.who}}"},
                output_name="said",
                output_kind="text",
            )
        ],
        variables=[TaskVariable(name="who", type="string", label="Who")],
    )

    lc: list = []
    await _collect(
        run_task(
            task,
            {"who": "world"},
            state=stub_state,
            session_id="run-lc-1",
            owner_id=TEST_OWNER_ID,
            llm=FakeListChatModel(responses=["unused"]),
            lc_messages=lc,
        )
    )
    assert isinstance(lc[0], HumanMessage)
    assert "Echo" in lc[0].content or task.title in lc[0].content
    ai = next(m for m in lc if isinstance(m, AIMessage))
    assert ai.tool_calls and ai.tool_calls[0]["id"] == "s1"
    assert ai.tool_calls[0]["name"] == "echo_tool"
    assert ai.tool_calls[0]["args"] == {"text": "hi world"}
    tm = next(m for m in lc if isinstance(m, ToolMessage))
    assert tm.tool_call_id == "s1"
    assert "echo:hi world" in tm.content


@pytest.mark.asyncio
async def test_runner_lc_messages_marks_failed_step_as_error(monkeypatch, stub_state):
    await reset_task_tables(SavedTask, SavedArtifact)
    monkeypatch.setattr("app.tasks.runner.tool_registry.discover_tools", lambda: [echo_tool])
    task = await _persist_task(
        steps=[
            TaskStep(
                id="s1",
                kind="tool",
                title="Boom",
                tool="echo_tool",
                args_template={"text": "{{var.missing}}"},
                output_name="x",
                output_kind="text",
            )
        ],
        variables=[],
    )
    lc: list = []
    await _collect(
        run_task(
            task,
            {},
            state=stub_state,
            session_id="run-lc-fail",
            owner_id=TEST_OWNER_ID,
            llm=FakeListChatModel(responses=["unused"]),
            lc_messages=lc,
        )
    )
    tm = next(m for m in lc if isinstance(m, ToolMessage))
    assert tm.status == "error"
    assert tm.tool_call_id == "s1"


@pytest.mark.asyncio
async def test_runner_report_step_emits_text_delta_with_artifact_links(monkeypatch, stub_state):
    """A `kind=report` step substitutes prior artifact ids and streams as text-delta.
    No tool-input / tool-output events — it renders inline in the assistant text."""
    await reset_task_tables(SavedTask, SavedArtifact)
    monkeypatch.setattr("app.tasks.runner.tool_registry.discover_tools", lambda: [echo_tool])

    @tool(response_format="content_and_artifact")
    def make_table() -> tuple[str, dict]:
        """Return a fake table artifact."""
        return ("ok", {"id": "art_rep111111", "kind": "table", "title": "Rev"})

    monkeypatch.setattr("app.tasks.runner.tool_registry.discover_tools", lambda: [make_table])

    task = await _persist_task(
        steps=[
            TaskStep(
                id="s1",
                kind="tool",
                title="Build table",
                tool="make_table",
                args_template={},
                output_name="table",
                output_kind="rows",
            ),
            TaskStep(
                id="s2",
                kind="report",
                title="Results",
                prompt="### Revenue\n\n[Rev](artifact:{{s1.artifact_id}})\n",
                output_name="report",
                output_kind="text",
            ),
        ],
        variables=[],
    )

    events = await _collect(
        run_task(
            task,
            {},
            state=stub_state,
            session_id="run-report-1",
            owner_id=TEST_OWNER_ID,
            llm=FakeListChatModel(responses=["unused"]),
        )
    )
    types = [e["type"] for e in events]
    # Report step must NOT emit tool-input/output for s2 — it streams as text.
    tool_inputs = [e for e in events if e["type"] == "tool-input-available"]
    assert all(e["toolCallId"] != "s2" for e in tool_inputs)
    assert "tool-output-error" not in types
    # The report's text part must open AFTER the preceding tool-output so the
    # AI SDK renders it below the tool card, not at the top of the message.
    s1_output_idx = next(
        i
        for i, e in enumerate(events)
        if e["type"] == "tool-output-available" and e["toolCallId"] == "s1"
    )
    text_starts = [i for i, e in enumerate(events) if e["type"] == "text-start"]
    report_text_start = next(i for i in text_starts if i > s1_output_idx)
    report_id = events[report_text_start]["id"]
    report_deltas = [e for e in events if e["type"] == "text-delta" and e["id"] == report_id]
    body = "".join(e["delta"] for e in report_deltas)
    assert "[Rev](artifact:art_rep111111)" in body
    assert "### Revenue" in body


@pytest.mark.asyncio
async def test_runner_report_persists_after_tool_messages(monkeypatch, stub_state):
    """The report's text must persist into a TRAILING AIMessage (no tool_calls)
    that comes AFTER the tool-call AIMessage + ToolMessages. /sessions reload
    appends text-parts before tool-parts within a single AIMessage, so keeping
    report text in the same AIMessage as tool_calls flips the order on reload.
    """
    await reset_task_tables(SavedTask, SavedArtifact)

    @tool(response_format="content_and_artifact")
    def make_table() -> tuple[str, dict]:
        """Fake artifact tool."""
        return ("ok", {"id": "art_persist111", "kind": "table", "title": "T"})

    monkeypatch.setattr("app.tasks.runner.tool_registry.discover_tools", lambda: [make_table])

    task = await _persist_task(
        steps=[
            TaskStep(
                id="s1",
                kind="tool",
                title="Build",
                tool="make_table",
                args_template={},
                output_name="t",
                output_kind="rows",
            ),
            TaskStep(
                id="s2",
                kind="report",
                title="Results",
                prompt="### Results\n\n[T](artifact:{{s1.artifact_id}})\n",
                output_name="report",
                output_kind="text",
            ),
        ],
        variables=[],
    )
    lc: list = []
    await _collect(
        run_task(
            task,
            {},
            state=stub_state,
            session_id="run-report-persist",
            owner_id=TEST_OWNER_ID,
            llm=FakeListChatModel(responses=["unused"]),
            lc_messages=lc,
        )
    )

    ai_msgs = [(i, m) for i, m in enumerate(lc) if isinstance(m, AIMessage)]
    tool_msg_indices = [i for i, m in enumerate(lc) if isinstance(m, ToolMessage)]
    # The first AIMessage carries tool_calls. Its content must NOT include the
    # report body (would render above tool cards on reload).
    _, first_ai = ai_msgs[0]
    assert first_ai.tool_calls and first_ai.tool_calls[0]["id"] == "s1"
    assert "[T](artifact:art_persist111)" not in (first_ai.content or "")
    # A second AIMessage holds the report body, sitting AFTER all ToolMessages.
    trailing = [(i, m) for i, m in ai_msgs if i > max(tool_msg_indices)]
    assert trailing, "expected a trailing AIMessage with report text"
    _, report_ai = trailing[0]
    assert not (report_ai.tool_calls or [])
    assert "[T](artifact:art_persist111)" in (report_ai.content or "")


@pytest.mark.asyncio
async def test_persist_task_run_checkpoint_roundtrip():
    """persist_task_run_checkpoint writes LC messages such that the AsyncSqliteSaver
    can be re-read via aget_tuple — this is what /sessions/{id}/messages relies on."""
    from langgraph.checkpoint.memory import InMemorySaver

    from app.tasks.runner import persist_task_run_checkpoint

    saver = InMemorySaver()
    msgs = [
        HumanMessage(content="Run task **T**"),
        AIMessage(
            content="ok",
            tool_calls=[{"id": "s1", "name": "echo_tool", "args": {"text": "x"}}],
        ),
        ToolMessage(content="echo:x", tool_call_id="s1"),
    ]
    await persist_task_run_checkpoint(saver, "sess-persist-1", msgs)
    tup = await saver.aget_tuple({"configurable": {"thread_id": "sess-persist-1"}})
    assert tup is not None
    saved = tup.checkpoint["channel_values"]["messages"]
    kinds = [type(m).__name__ for m in saved]
    assert kinds == ["HumanMessage", "AIMessage", "ToolMessage"]
    assert saved[1].tool_calls[0]["id"] == "s1"
    assert saved[2].tool_call_id == "s1"
