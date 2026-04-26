import json
from types import SimpleNamespace

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.tools import tool
from sqlmodel import delete

from app.db import async_session, init_db
from app.models import SavedArtifact, SavedTask
from app.tasks.runner import run_task
from app.tasks.schemas import TaskDTO, TaskStep, TaskVariable
from app.tasks.storage import upsert_task


@tool
def echo_tool(text: str) -> str:
    """Return the supplied text unchanged."""
    return f"echo:{text}"


def _state():
    # MCP registry has `.tools` returning a list. Plain SimpleNamespace works.
    registry = SimpleNamespace(tools=[])
    return SimpleNamespace(mcp_registry=registry)


async def _collect(stream) -> list[dict]:
    out: list[dict] = []
    async for line in stream:
        if line.startswith("data: ") and "[DONE]" not in line:
            try:
                out.append(json.loads(line.removeprefix("data: ").strip()))
            except json.JSONDecodeError:
                continue
    return out


async def _persist_task(*, steps: list[TaskStep], variables: list[TaskVariable]):
    dto = TaskDTO(
        id="tsk_runtest1234",
        title="Runner test",
        variables=variables,
        steps=steps,
    )
    return await upsert_task(dto)


@pytest.mark.asyncio
async def test_runner_executes_tool_step_with_substitution(monkeypatch):
    await init_db()
    async with async_session() as s:
        await s.execute(delete(SavedTask))
        await s.execute(delete(SavedArtifact))
        await s.commit()

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
            state=_state(),
            session_id="run-sess-1",
            llm=FakeListChatModel(responses=["unused"]),
        )
    )
    types = [e["type"] for e in events]
    assert "tool-input-start" in types
    assert "tool-input-available" in types
    assert "tool-output-available" in types
    output_evt = next(e for e in events if e["type"] == "tool-output-available")
    assert output_evt["output"] == "echo:hello world"
    assert "tool-output-error" not in types


@pytest.mark.asyncio
async def test_runner_runs_prompt_step_via_llm():
    await init_db()
    async with async_session() as s:
        await s.execute(delete(SavedTask))
        await s.commit()

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
            state=_state(),
            session_id="run-sess-prompt",
            llm=FakeListChatModel(responses=["Indices speed up reads."]),
        )
    )
    output = next(e for e in events if e["type"] == "tool-output-available")
    assert "Indices speed up reads." in output["output"]


@pytest.mark.asyncio
async def test_runner_subagent_step_exposes_artifact_id_for_chaining(monkeypatch):
    await init_db()
    async with async_session() as s:
        await s.execute(delete(SavedTask))
        await s.commit()

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
            state=_state(),
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
async def test_runner_halts_on_missing_variable(monkeypatch):
    await init_db()
    async with async_session() as s:
        await s.execute(delete(SavedTask))
        await s.commit()

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
            state=_state(),
            session_id="run-sess-fail",
            llm=FakeListChatModel(responses=["x"]),
        )
    )
    errors = [e for e in events if e["type"] == "tool-output-error"]
    assert len(errors) == 1 and errors[0]["toolCallId"] == "s1"
    started = [e for e in events if e["type"] == "tool-input-start"]
    assert all(e["toolCallId"] != "s2" for e in started)
