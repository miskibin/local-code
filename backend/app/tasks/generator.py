"""LLM-driven task generation from a finished agent run.

Reads the LangGraph checkpoint for a session, pulls tool calls + artifacts,
asks the LLM to distil it into a TaskDTO (variables hoisted, failed/junk
steps dropped), validates the JSON, persists.
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from loguru import logger
from sqlmodel import select

from app.db import async_session
from app.models import SavedArtifact
from app.tasks import coerce_lc_content
from app.tasks.schemas import TaskDTO, TaskStep, TaskVariable
from app.tasks.storage import create_task, to_dto

GENERATOR_SYSTEM = """You convert a finished agent run into a reusable Task.

A Task has variables (typed inputs) and ordered steps. Each step has exactly
one kind:
  - tool      → invoke a registered tool. Required: tool (name), args_template (JSON object).
  - code      → run Python. Required: code (string). See PYTHON CODE CONTRACT below.
  - subagent  → delegate to a named subagent. Required: subagent (name), prompt (string).
  - prompt    → single free-form LLM call. Required: prompt (string).

PYTHON CODE CONTRACT (kind=code):
  The code runs inside a sandboxed `python_exec`. Three helpers are pre-injected:
    - out(obj)             → surface obj as the step artifact.
                              list[dict] becomes a TABLE; dict/str/number becomes TEXT/JSON.
    - out_image(fig=None, *, title=None, caption=None)
                            → emit a matplotlib figure as a PNG IMAGE artifact.
                              MUST be used for any plot. Calling out(fig) on a Figure
                              object only stores its repr (e.g. "Figure(1000x600)") and
                              IS WRONG. With no arg captures plt.gcf().
    - read_artifact("art_xxx")
                            → load a prior artifact by literal id. Tables → DataFrame,
                              images → PNG bytes, text → str. The id MUST appear as a
                              literal string in the script source.

  RULES for code steps:
    - When the step produces a CHART/PLOT, the LAST line(s) MUST call out_image(fig).
      Set output_kind="chart" for these.
    - When the step produces a TABLE/rows, end with out(rows). output_kind="rows".
    - To consume a prior step's table, write
          df = read_artifact("{{<prevStepId>.artifact_id}}")
      Tables come back as a pandas DataFrame.
    - matplotlib + pandas are available. Subprocess, 20s timeout, no state across calls.

REFERENCE SYNTAX — strict, no shorthand:
  - {{var.<variable_name>}}            → a user-supplied variable
  - {{<stepId>.<output_name>}}         → an earlier step's named output

  Both forms MUST contain a dot. {{name}} alone is invalid and will fail at run
  time. The runner does no other substitution.

  References go inside string values (args_template fields, code, prompt). Do
  not wrap them in extra quotes; write them bare inside the surrounding string.

OUTPUT NAMES:
  - Each step declares a short snake_case `output_name` (e.g. "rows", "filtered",
    "summary"). Later steps reference that exact name.
  - SUBAGENT steps that delegate to the SQL agent automatically expose an extra
    `artifact_id` output (parsed from the agent's contract trailer
    `artifact_id=art_xxx; columns=...`). To pass that artifact to a later step,
    write {{<stepId>.artifact_id}}.

HARD RULES:
  - Drop failed steps and steps that produced nothing useful.
  - Hoist literal values that look like inputs (project names, paths, prefixes,
    thresholds) into variables. Mechanical IDs and tool-internal artefact ids
    are NOT variables.
  - Pick descriptive step titles. Each step.id is a short token (s1, s2, ...).
  - Keep step order matching execution order.
  - NEVER emit a tool step with `tool: "task"`. The `task` name is the agent's
    in-loop subagent dispatcher and is not callable from outside the agent. For
    delegations, emit a `subagent` step with the subagent name in `subagent`
    and the brief in `prompt`.
  - NEVER emit bare {{name}} references — always use {{var.name}} or
    {{stepId.output}}.

OUTPUT — STRICT JSON, NO commentary, NO markdown fences. Shape:
    {
      "title": str,
      "description": str,
      "variables": [{"name": str, "type": "string"|"number"|"boolean",
                     "label": str, "default": any, "required": bool}],
      "steps": [{
        "id": str, "kind": "tool"|"code"|"subagent"|"prompt",
        "title": str,
        "server"?: str, "tool"?: str, "args_template"?: object,
        "code"?: str, "subagent"?: str, "prompt"?: str,
        "output_name": str,
        "output_kind": "rows"|"text"|"chart"|"json"|"file"
      }]
    }
"""


def _extract_run_trace(messages: list[Any]) -> dict[str, Any]:
    user_prompt = ""
    tool_calls: list[dict[str, Any]] = []
    pending: dict[str, dict[str, Any]] = {}
    final_text = ""

    for m in messages:
        if isinstance(m, HumanMessage) or getattr(m, "type", None) == "human":
            text = coerce_lc_content(m.content)
            if text:
                user_prompt = text
        if isinstance(m, AIMessage) or getattr(m, "type", None) == "ai":
            text = coerce_lc_content(m.content)
            if text:
                final_text = text
            for tc in getattr(m, "tool_calls", None) or []:
                cid = tc.get("id")
                if not cid:
                    continue
                pending[cid] = {
                    "id": cid,
                    "name": tc.get("name"),
                    "args": tc.get("args") or {},
                    "result": None,
                    "error": None,
                }
        if isinstance(m, ToolMessage) or getattr(m, "type", None) == "tool":
            cid = getattr(m, "tool_call_id", None)
            entry = pending.get(cid) if cid else None
            if entry is None:
                continue
            text = coerce_lc_content(m.content)
            if getattr(m, "status", None) == "error":
                entry["error"] = text
            else:
                entry["result"] = text[:500]
            tool_calls.append(entry)
            pending.pop(cid, None)

    return {
        "user_prompt": user_prompt,
        "tool_calls": tool_calls,
        "final_text": final_text,
    }


async def _session_artifacts(session_id: str) -> list[dict[str, Any]]:
    async with async_session() as s:
        rows = (
            (await s.execute(select(SavedArtifact).where(SavedArtifact.session_id == session_id)))
            .scalars()
            .all()
        )
    return [
        {
            "id": r.id,
            "kind": r.kind,
            "title": r.title,
            "summary": r.summary,
            "source_kind": r.source_kind,
            "source_code": (r.source_code or "")[:2000],
        }
        for r in rows
    ]


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.+?)\s*```$", text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1)
    return text


def _parse_task_json(raw: str) -> dict[str, Any]:
    cleaned = _strip_code_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Attempt to salvage: locate the outermost JSON object.
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"generator did not return valid JSON: {e}") from e


def _ensure_step_ids(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, step in enumerate(steps):
        step.setdefault("id", f"s{i + 1}")
        step.setdefault("title", step["id"])
        step.setdefault("output_name", "output")
        step.setdefault("output_kind", "text")
        out.append(step)
    return out


async def generate_task_from_run(
    *,
    session_id: str,
    messages: list[Any],
    llm: BaseChatModel,
) -> TaskDTO:
    trace = _extract_run_trace(messages)
    artifacts = await _session_artifacts(session_id)

    payload = {
        "user_prompt": trace["user_prompt"],
        "tool_calls": trace["tool_calls"],
        "final_assistant_text": trace["final_text"][:1500],
        "artifacts": artifacts,
    }
    user_msg = (
        "Convert this run into a Task JSON object. "
        "Run trace:\n```json\n" + json.dumps(payload, ensure_ascii=False)[:12000] + "\n```"
    )

    response = await llm.ainvoke(
        [
            HumanMessage(content=GENERATOR_SYSTEM),
            HumanMessage(content=user_msg),
        ]
    )
    raw = coerce_lc_content(getattr(response, "content", response))
    logger.debug(f"generator raw output (first 500): {raw[:500]}")
    parsed = _parse_task_json(raw)

    parsed_steps = _ensure_step_ids(parsed.get("steps") or [])
    dto = TaskDTO(
        id="",
        title=parsed.get("title") or "Untitled task",
        description=parsed.get("description", ""),
        source_session_id=session_id,
        variables=[TaskVariable(**v) for v in parsed.get("variables") or []],
        steps=[TaskStep(**s) for s in parsed_steps],
    )
    row = await create_task(dto)
    logger.info(f"task generated id={row.id} steps={len(dto.steps)} vars={len(dto.variables)}")
    return to_dto(row)
