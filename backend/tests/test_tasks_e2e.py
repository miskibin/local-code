"""End-to-end runs against the real /chat endpoint with a stub LLM.

Each test imports a task JSON fixture via /tasks/import, then drives /chat
with task_run and walks the SSE stream, asserting no step errored.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.checkpoint.memory import InMemorySaver

from app.models import ChatMessage, ChatSession, SavedArtifact, SavedTask
from tests.conftest import parse_sse_events, reset_task_tables

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class _StubLLM(FakeListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def _bootstrap_app(llm_responses: list[str]):
    from app.main import create_app

    app = create_app()
    app.state.llm_cache = {"gemma4:e4b": _StubLLM(responses=llm_responses)}
    app.state.checkpointer = InMemorySaver()
    app.state.mcp_registry = type("R", (), {"tools": []})()
    return app


async def _run_task(ac: AsyncClient, *, task_id: str, variables: dict, session_id: str):
    body = {
        "id": session_id,
        "messages": [
            {
                "id": "u1",
                "role": "user",
                "parts": [{"type": "text", "text": "Run task"}],
            }
        ],
        "reset": True,
        "model": "gemma4:e4b",
        "task_run": {"task_id": task_id, "variables": variables},
    }
    async with ac.stream("POST", "/chat", json=body) as resp:
        assert resp.status_code == 200, await resp.aread()
        raw = (await resp.aread()).decode("utf-8")
    return parse_sse_events(raw.splitlines())


@pytest.mark.asyncio
async def test_e2e_prompt_task_resolves_var_refs():
    await reset_task_tables(ChatMessage, ChatSession, SavedArtifact, SavedTask)
    app = _bootstrap_app(["A small CLI for time."])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        imported = await ac.post("/tasks/import", json=_load_fixture("task_prompt.json"))
        assert imported.status_code == 200, imported.text
        task_id = imported.json()["id"]

        events = await _run_task(
            ac,
            task_id=task_id,
            variables={
                "cli_purpose": "uptime monitor",
                "team_expertise": "python",
                "main_priorities": "speed",
            },
            session_id="sess-prompt-e2e",
        )
        errors = [e for e in events if e["type"] == "tool-output-error"]
        assert not errors, errors
        # Prompt-kind steps stream as text deltas, no tool wrapper.
        deltas = "".join(e["delta"] for e in events if e["type"] == "text-delta")
        assert "A small CLI for time." in deltas
        assert "Request Detailed CLI Requirements" in deltas


@pytest.mark.asyncio
async def test_e2e_task_run_messages_reload_via_checkpointer():
    """After a task run, GET /sessions/{id}/messages must return the run's tool steps,
    not an empty list — the run is persisted to the LangGraph checkpointer like chat."""
    await reset_task_tables(ChatMessage, ChatSession, SavedArtifact, SavedTask)
    app = _bootstrap_app(["A small CLI for time."])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        imported = await ac.post("/tasks/import", json=_load_fixture("task_prompt.json"))
        assert imported.status_code == 200, imported.text
        task_id = imported.json()["id"]

        sid = "sess-reload-e2e"
        await _run_task(
            ac,
            task_id=task_id,
            variables={
                "cli_purpose": "uptime monitor",
                "team_expertise": "python",
                "main_priorities": "speed",
            },
            session_id=sid,
        )
        r = await ac.get(f"/sessions/{sid}/messages")
        assert r.status_code == 200
        body = r.json()
        roles = [m["role"] for m in body]
        assert "user" in roles
        assert "assistant" in roles
        assistant_msg = next(m for m in body if m["role"] == "assistant")
        # The prompt-step output should be in the assistant content.
        text_parts = [p for p in assistant_msg["parts"] if p["type"] == "text"]
        assert any("CLI" in p.get("text", "") for p in text_parts)


@pytest.mark.asyncio
async def test_e2e_subagent_then_code_propagates_artifact_id(python_sandbox):
    """SUBAGENT step exposes artifact_id; CODE step interpolates it."""
    await reset_task_tables(ChatMessage, ChatSession, SavedArtifact, SavedTask)
    sql_response = (
        "Top spenders computed.\nartifact_id=art_e2etest1234; columns=FirstName,TotalSpend"
    )
    app = _bootstrap_app([sql_response])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        imported = await ac.post("/tasks/import", json=_load_fixture("task_chart.json"))
        assert imported.status_code == 200, imported.text
        task_id = imported.json()["id"]

        events = await _run_task(
            ac,
            task_id=task_id,
            variables={"database_name": "Chinook"},
            session_id="sess-chart-e2e",
        )
        errors = [e for e in events if e["type"] == "tool-output-error"]
        assert not errors, errors
        outputs = {e["toolCallId"]: e for e in events if e["type"] == "tool-output-available"}
        assert set(outputs) == {"s1", "s2"}
        # The code step's output should contain the parsed artifact_id.
        assert "art_e2etest1234" in str(outputs["s2"]["output"])
        # Both steps should have produced an artifact (sql trailer + python out).
        artifacts = [e for e in events if e["type"] == "data-artifact"]
        assert any(e["data"]["toolCallId"] == "s2" for e in artifacts)
