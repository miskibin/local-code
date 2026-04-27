import json

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from sqlmodel import select

from app.db import async_session
from app.models import SavedArtifact, SavedTask
from app.tasks.generator import generate_task_from_run
from tests.conftest import reset_task_tables


def _trace_messages():
    return [
        HumanMessage(content="find top customers in Chinook by total spend"),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call1",
                    "name": "sql_query",
                    "args": {"sql": "SELECT * FROM customers LIMIT 5"},
                }
            ],
        ),
        ToolMessage(content="art_abc · table 5 rows", tool_call_id="call1"),
        AIMessage(content="See the table above."),
    ]


@pytest.mark.asyncio
async def test_generate_task_persists_and_validates_json():
    await reset_task_tables(SavedTask, SavedArtifact)

    response_json = json.dumps(
        {
            "title": "Top customers report",
            "description": "Top N customers by total spend.",
            "variables": [
                {
                    "name": "limit",
                    "type": "number",
                    "label": "Limit",
                    "default": 5,
                    "required": True,
                }
            ],
            "steps": [
                {
                    "id": "s1",
                    "kind": "tool",
                    "title": "Query top customers",
                    "tool": "sql_query",
                    "args_template": {"sql": "SELECT * FROM customers LIMIT {{var.limit}}"},
                    "output_name": "rows",
                    "output_kind": "rows",
                }
            ],
        }
    )
    llm = FakeListChatModel(responses=[response_json])
    dto = await generate_task_from_run(session_id="sess-gen", messages=_trace_messages(), llm=llm)
    assert dto.id.startswith("tsk_")
    assert dto.title == "Top customers report"
    assert len(dto.variables) == 1 and dto.variables[0].name == "limit"
    assert dto.steps[0].tool == "sql_query"

    async with async_session() as s:
        rows = list((await s.execute(select(SavedTask))).scalars())
    assert any(r.id == dto.id for r in rows)


@pytest.mark.asyncio
async def test_generate_task_strips_markdown_code_fence():
    await reset_task_tables(SavedTask)

    fenced = "```json\n" + json.dumps({"title": "T", "variables": [], "steps": []}) + "\n```"
    llm = FakeListChatModel(responses=[fenced])
    dto = await generate_task_from_run(session_id="sess-fence", messages=_trace_messages(), llm=llm)
    assert dto.title == "T"


@pytest.mark.asyncio
async def test_generate_task_raises_on_garbage():
    await reset_task_tables(SavedTask)

    llm = FakeListChatModel(responses=["not json at all"])
    with pytest.raises(ValueError):
        await generate_task_from_run(session_id="sess-bad", messages=_trace_messages(), llm=llm)


def _sql_subagent_trace(artifact_id: str = "art_genx111111"):
    return [
        HumanMessage(content="top genres by revenue"),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call1",
                    "name": "task",
                    "args": {
                        "subagent_type": "sql-agent",
                        "description": "Calculate revenue by genre",
                    },
                }
            ],
        ),
        ToolMessage(
            content=f"Top genres computed.\nartifact_id={artifact_id}; columns=Genre,TotalRevenue",
            tool_call_id="call1",
        ),
        AIMessage(content="See the table."),
    ]


def _subagent_task_json() -> str:
    return json.dumps(
        {
            "title": "Genre Revenue",
            "description": "",
            "variables": [],
            "steps": [
                {
                    "id": "s1",
                    "kind": "subagent",
                    "title": "Calculate Revenue by Genre",
                    "subagent": "sql-agent",
                    "prompt": "Join InvoiceLine, Track, Genre and total revenue per genre.",
                    "output_name": "revenue_data",
                    "output_kind": "rows",
                }
            ],
        }
    )


@pytest.mark.asyncio
async def test_subagent_sql_step_replaced_with_sql_query_tool():
    """Generator post-processing should bake the captured SQL into a sql_query tool step."""
    from app.artifact_store import create_artifact

    await reset_task_tables(SavedTask, SavedArtifact)
    captured_sql = (
        "SELECT g.Name AS Genre, SUM(il.UnitPrice * il.Quantity) AS TotalRevenue "
        "FROM InvoiceLine il JOIN Track t ON t.TrackId = il.TrackId "
        "JOIN Genre g ON g.GenreId = t.GenreId GROUP BY g.Name LIMIT 200"
    )
    await create_artifact(
        kind="table",
        title="Genre Revenue",
        payload={"columns": [{"key": "Genre", "label": "Genre"}], "rows": []},
        summary="t",
        source_kind="sql",
        source_code=captured_sql,
        session_id="sess-genre",
        artifact_id="art_genx111111",
    )

    llm = FakeListChatModel(responses=[_subagent_task_json()])
    dto = await generate_task_from_run(
        session_id="sess-genre", messages=_sql_subagent_trace(), llm=llm
    )
    assert len(dto.steps) == 1
    step = dto.steps[0]
    assert step.kind == "tool"
    assert step.tool == "sql_query"
    assert step.args_template == {"sql": captured_sql}
    assert step.output_kind == "rows"
    assert step.subagent is None
    assert step.prompt is None
    assert step.id == "s1"
    assert step.output_name == "revenue_data"


@pytest.mark.asyncio
async def test_subagent_sql_step_kept_when_artifact_missing():
    """If captured SQL artifact isn't in the session, leave the subagent step alone."""
    await reset_task_tables(SavedTask, SavedArtifact)

    llm = FakeListChatModel(responses=[_subagent_task_json()])
    dto = await generate_task_from_run(
        session_id="sess-no-art", messages=_sql_subagent_trace(), llm=llm
    )
    assert dto.steps[0].kind == "subagent"
    assert dto.steps[0].subagent == "sql-agent"
