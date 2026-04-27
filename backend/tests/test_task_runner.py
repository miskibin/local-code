import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.tools import tool

from app.models import SavedArtifact, SavedTask
from app.tasks.runner import run_task
from app.tasks.schemas import TaskDTO, TaskStep, TaskVariable
from app.tasks.storage import upsert_task
from tests.conftest import parse_sse_events, reset_task_tables


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
    return await upsert_task(dto)


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
