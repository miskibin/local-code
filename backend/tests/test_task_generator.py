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
