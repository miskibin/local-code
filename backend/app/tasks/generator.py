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

from app.artifact_store import get_artifact
from app.db import async_session
from app.models import SavedArtifact
from app.tasks import coerce_lc_content
from app.tasks.schemas import TaskDTO, TaskRole, TaskStep, TaskVariable
from app.tasks.storage import create_task, to_dto

_ROLE_IDS: frozenset[str] = frozenset(TaskRole.__args__)

_SQL_SUBAGENT_NAME = "sql-agent"
_ARTIFACT_ID_RE = re.compile(r"\bartifact_id\s*=\s*(art_[A-Za-z0-9]+)")

GENERATOR_SYSTEM = """You convert a finished agent run into a reusable Task.

A Task has variables (typed inputs) and ordered steps. Each step has exactly
one kind:
  - tool      → invoke a registered tool. Required: tool (name), args_template (JSON object).
  - code      → run Python. Required: code (string). See PYTHON CODE CONTRACT below.
  - subagent  → delegate to a named subagent. Required: subagent (name), prompt (string).
  - prompt    → single free-form LLM call. Required: prompt (string).

PYTHON CODE CONTRACT (kind=code):
  The code runs inside a sandboxed `python_exec`. Helpers are pre-injected:
    - out(obj)             → surface obj as the step artifact.
                              list[dict] becomes a TABLE; dict/str/number becomes TEXT/JSON.
    - out_sql_list(items, *, quote="'")
                            → surface a SQL fragment built from a list, e.g.
                              ["GenreId","AlbumId"] -> "'GenreId', 'AlbumId'".
                              USE THIS (not out(list)) when a downstream tool step
                              needs the list interpolated into SQL via
                              {{<thisStepId>.<output_name>}}. Pass quote='"' for
                              identifier lists. The step that COMPUTES the list
                              must be the same step that calls out_sql_list — do
                              NOT add a separate "format for SQL" step that reads
                              the prior list and re-emits it.
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
  - Every non-report step must be CONSUMED by a later step. If step A produces
    a list/value that step B uses, step B's args_template / code / prompt MUST
    reference {{<A.id>.<A.output_name>}} (or {{<A.id>.artifact_id}} for code
    steps that read_artifact). Do NOT hardcode the value from the run trace —
    hardcoded downstream values silently go stale on re-run with new inputs.
  - When the consumer is a SQL `tool` step:
      1. Have the producing `code` step end with `out_sql_list(items)` (or
         out_sql_list(items, quote='"') for identifier lists, quote='' for
         numeric IDs). Its output_name then carries a ready-to-paste SQL
         fragment.
      2. Inside the consumer's args_template SQL string, paste the fragment
         literally with `{{<producerId>.<output_name>}}`.
    Do NOT introduce a separate "Prepare SQL list" code step in between — the
    producer formats and the consumer interpolates. One step each.

WORKED PATTERN (different domain, illustrative — invent your own steps for
the actual run):
    Goal: total invoice value for VIP customers (segment = top spenders).
    Steps:
      s1 (subagent, sql-agent): query top-N CustomerId by lifetime spend.
                                 → output_name="vip_rows"
      s2 (code): df = read_artifact("{{s1.artifact_id}}")
                 ids = df["CustomerId"].tolist()
                 out_sql_list(ids, quote="")     # numeric IDs → no quotes
                 → output_name="vip_id_list"
      s3 (tool sql_query): args_template = {
           "sql": "SELECT SUM(Total) FROM Invoice WHERE CustomerId IN ({{s2.vip_id_list}})"
         }
    Note: s2 derives `ids` from s1 at run time (NOT a Python literal copied
    from the run trace), and s3's SQL contains zero hardcoded IDs — every
    value that varies between runs flows through a {{...}} reference. Apply
    the same shape to whatever domain the actual run uses.
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

ROLE — pick exactly one of these ids based on who would naturally re-run the
task. Use null only if the run gives no signal at all.
  - "local_product_owner"  → site/feature-level PO work: backlog grooming,
                              acceptance checks, ad-hoc digging into one
                              product area's data.
  - "fot_leader"           → feature/operations team leader: cross-team
                              status, delivery health, blockers, capacity.
  - "area_product_owner"   → area-level PO: roadmap rollups across multiple
                              local POs, portfolio metrics, area KPIs.
  - "product_manager"      → broader PM work: market/customer analysis,
                              strategy artefacts, exec-facing reports.

OUTPUT — STRICT JSON, NO commentary, NO markdown fences. Shape:
    {
      "title": str,
      "description": str,
      "role": "local_product_owner"|"fot_leader"|"area_product_owner"|"product_manager"|null,
      "variables": [{"name": str, "type": "string"|"number"|"boolean",
                     "label": str, "default": any, "required": bool}],
      "steps": [{
        "id": str, "kind": "tool"|"code"|"subagent"|"prompt",
        "title": str,
        "tool"?: str, "args_template"?: object,
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


async def _inline_sql_subagent_steps(
    steps: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
) -> None:
    """Rewrite kind=subagent (sql-agent) steps into deterministic sql_query tool steps.

    Uses the actual SQL captured on the SavedArtifact produced by the original
    sub-agent run, so re-running the task doesn't re-ask the LLM to compose SQL.
    """
    sql_calls = [
        tc
        for tc in tool_calls
        if tc.get("name") == "task"
        and (tc.get("args") or {}).get("subagent_type") == _SQL_SUBAGENT_NAME
    ]
    sql_steps = [
        s for s in steps if s.get("kind") == "subagent" and s.get("subagent") == _SQL_SUBAGENT_NAME
    ]
    for step, call in zip(sql_steps, sql_calls, strict=False):
        m = _ARTIFACT_ID_RE.search(call.get("result") or "")
        if not m:
            continue
        artifact = await get_artifact(m.group(1))
        if artifact is None or artifact.source_kind != "sql" or not artifact.source_code:
            continue
        step["kind"] = "tool"
        step["tool"] = "sql_query"
        step["args_template"] = {"sql": artifact.source_code}
        step["output_kind"] = "rows"
        step.pop("subagent", None)
        step.pop("prompt", None)


_ARTIFACT_STEP_KINDS = {"tool", "code", "subagent"}


def _append_report_step(steps: list[dict[str, Any]]) -> None:
    """Append a deterministic kind=report step that re-renders prior artifacts.

    Body is markdown with `[Title](artifact:{{stepId.artifact_id}})` per
    artifact-producing step — the frontend Markdown renderer turns those into
    inline tables / images. No-op if the task has no artifact-producing steps.
    """
    art_steps = [s for s in steps if s.get("kind") in _ARTIFACT_STEP_KINDS]
    if not art_steps:
        return
    sections = []
    for s in art_steps:
        title = s.get("title") or s["id"]
        ref = f"{{{{{s['id']}.artifact_id}}}}"
        sections.append(f"**{title}**\n\n[{title}](artifact:{ref})")
    body = "## Results\n\n" + "\n\n".join(sections) + "\n"
    steps.append(
        {
            "id": f"s{len(steps) + 1}",
            "kind": "report",
            "title": "Results",
            "prompt": body,
            "output_name": "report",
            "output_kind": "text",
        }
    )


async def generate_task_from_run(
    *,
    session_id: str,
    messages: list[Any],
    llm: BaseChatModel,
    owner_id: str,
    creator: str,
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
    await _inline_sql_subagent_steps(parsed_steps, trace["tool_calls"])
    _append_report_step(parsed_steps)
    raw_role = parsed.get("role")
    role = raw_role if raw_role in _ROLE_IDS else None
    dto = TaskDTO(
        id="",
        title=parsed.get("title") or "Untitled task",
        description=parsed.get("description", ""),
        source_session_id=session_id,
        variables=[TaskVariable(**v) for v in parsed.get("variables") or []],
        steps=[TaskStep(**s) for s in parsed_steps],
        role=role,
        creator=creator,
    )
    row = await create_task(dto, owner_id)
    logger.info(f"task generated id={row.id} steps={len(dto.steps)} vars={len(dto.variables)}")
    return to_dto(row)
