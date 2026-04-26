"""Hybrid task runner.

TOOL/CODE steps run scripted (direct tool/python_exec invocation).
SUBAGENT/PROMPT steps run through an LLM call (with optional tool binding).

All steps emit SSE events compatible with the existing chat stream so the
frontend renders them as ordinary tool calls / artifacts. On any step
failure we halt and surface the error — no retry, no skip.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from loguru import logger

from app import tool_registry
from app.artifact_store import (
    build_and_persist_tool_artifact,
    persist_tool_artifact,
    run_python_artifact,
)
from app.db import async_session
from app.graphs.main_agent import default_subagents
from app.models import ChatMessage, ChatSession, SavedTask
from app.streaming import sse
from app.tasks.schemas import TaskDTO, TaskStep
from app.tasks.storage import to_dto
from app.tasks.substitution import SubstitutionError, substitute

_CONTENT_AND_ARTIFACT_LEN = 2  # langchain (summary, artifact) tuple shape

_ARTIFACT_ID_RE = re.compile(r"\bartifact_id\s*=\s*(art_[A-Za-z0-9]+)")
_COLUMNS_RE = re.compile(r"\bcolumns\s*=\s*([A-Za-z0-9_,\s]+)")


def _extract_subagent_outputs(text: str) -> dict[str, Any]:
    """Subagent prompts ask the agent to end with `artifact_id=...; columns=...`.

    Surface these as sibling outputs so later steps can reference
    `{{stepId.artifact_id}}` directly.
    """
    extra: dict[str, Any] = {}
    m = _ARTIFACT_ID_RE.search(text or "")
    if m:
        extra["artifact_id"] = m.group(1)
    c = _COLUMNS_RE.search(text or "")
    if c:
        cols = [s.strip() for s in c.group(1).split(",") if s.strip()]
        if cols:
            extra["columns"] = cols
    return extra


def _now() -> datetime:
    return datetime.now(UTC)


async def _all_tools(state) -> list[BaseTool]:
    local = tool_registry.discover_tools()
    mcp = state.mcp_registry.tools if hasattr(state, "mcp_registry") else []
    return local + mcp


def _emit_text_delta(text_id: str, delta: str) -> str:
    return sse({"type": "text-delta", "id": text_id, "delta": delta})


def _emit_input_start(step_id: str, name: str) -> str:
    return sse({"type": "tool-input-start", "toolCallId": step_id, "toolName": name})


def _emit_input(step_id: str, name: str, args: object) -> str:
    return sse(
        {
            "type": "tool-input-available",
            "toolCallId": step_id,
            "toolName": name,
            "input": args,
        }
    )


def _emit_output(step_id: str, output: object) -> str:
    return sse({"type": "tool-output-available", "toolCallId": step_id, "output": output})


def _emit_error(step_id: str, error_text: str) -> str:
    return sse({"type": "tool-output-error", "toolCallId": step_id, "errorText": error_text})


def _emit_artifact(step_id: str, row) -> str:
    return sse(
        {
            "type": "data-artifact",
            "id": row.id,
            "data": {
                "toolCallId": step_id,
                "artifactId": row.id,
                "kind": row.kind,
                "title": row.title,
                "summary": row.summary,
                "updatedAt": row.updated_at.isoformat(),
            },
        }
    )


def _coerce_summary(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(str(c.get("text", "")))
            else:
                parts.append(str(c))
        return "".join(parts)
    return str(content)


async def _run_tool_step(
    step: TaskStep,
    args: dict[str, Any],
    *,
    tools_by_key: dict[tuple[str | None, str], BaseTool],
    session_id: str,
) -> tuple[Any, dict[str, Any]]:
    """Resolve + invoke a registered/MCP tool. Returns (output, outputs_dict)."""
    if not step.tool:
        raise ValueError(f"step {step.id}: tool name required for kind=tool")
    server_key = step.server if step.server and step.server != "builtin" else None
    tool = tools_by_key.get((server_key, step.tool)) or tools_by_key.get((None, step.tool))
    if tool is None:
        raise LookupError(f"tool {step.tool!r} not available (server={step.server})")
    config = {"configurable": {"thread_id": session_id}}
    raw = await tool.ainvoke(args, config=config)
    artifact: dict[str, Any] | None = None
    if isinstance(raw, tuple) and len(raw) == _CONTENT_AND_ARTIFACT_LEN:
        summary, artifact = raw
    else:
        summary = raw
    summary_text = _coerce_summary(summary)
    if isinstance(artifact, dict) and artifact and not artifact.get("id"):
        row = await persist_tool_artifact(artifact=artifact, session_id=session_id)
        artifact = {**artifact, "id": row.id}
    outputs: dict[str, Any] = {step.output_name: artifact or summary_text}
    if isinstance(artifact, dict) and artifact.get("id"):
        outputs["artifact_id"] = artifact["id"]
    else:
        # Tool may have echoed `art_...` in its summary (e.g. python_exec).
        outputs.update(_extract_subagent_outputs(summary_text))
    return summary_text, outputs


async def _run_code_step(
    step: TaskStep,
    code: str,
    *,
    session_id: str,
) -> tuple[Any, dict[str, Any]]:
    if not code:
        raise ValueError(f"step {step.id}: code required for kind=code")
    result = await run_python_artifact(code)
    config = {"configurable": {"thread_id": session_id}}
    summary, artifact = await build_and_persist_tool_artifact(
        result=result, source_kind="python", source_code=code, config=config
    )
    outputs: dict[str, Any] = {step.output_name: artifact}
    if isinstance(artifact, dict) and artifact.get("id"):
        outputs["artifact_id"] = artifact["id"]
    return summary, outputs


async def _run_prompt_step(
    step: TaskStep,
    prompt: str,
    *,
    llm: BaseChatModel,
) -> tuple[Any, dict[str, Any]]:
    if not prompt:
        raise ValueError(f"step {step.id}: prompt required for kind=prompt")
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    text = _coerce_summary(getattr(response, "content", response))
    return text, {step.output_name: text}


async def _run_subagent_step(
    step: TaskStep,
    prompt: str,
    *,
    llm: BaseChatModel,
    all_tools: list[BaseTool],
    session_id: str,
) -> tuple[Any, dict[str, Any]]:
    if not prompt:
        raise ValueError(f"step {step.id}: prompt required for kind=subagent")
    target = step.subagent or ""
    spec = next((s for s in default_subagents() if s["name"] == target), None)
    system = spec["system_prompt"] if spec else "You are a helpful sub-agent."
    tool_names: list[str] = list(spec.get("tools", [])) if spec else []
    bound_tools = [t for t in all_tools if t.name in tool_names]
    chain = llm.bind_tools(bound_tools) if bound_tools else llm

    messages: list[Any] = [HumanMessage(content=f"{system}\n\n{prompt}")]
    last_text = ""
    for _ in range(4):  # cap subagent ReAct loop to keep tasks deterministic-ish
        response = await chain.ainvoke(messages)
        messages.append(response)
        text = _coerce_summary(getattr(response, "content", response))
        last_text = text or last_text
        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            break
        config = {"configurable": {"thread_id": session_id}}
        for tc in tool_calls:
            tool = next((t for t in bound_tools if t.name == tc["name"]), None)
            if tool is None:
                messages.append(
                    ToolMessage(content=f"tool {tc['name']} not bound", tool_call_id=tc["id"])
                )
                continue
            raw = await tool.ainvoke(tc.get("args") or {}, config=config)
            if isinstance(raw, tuple) and len(raw) == _CONTENT_AND_ARTIFACT_LEN:
                tool_text, _ = raw
            else:
                tool_text = raw
            messages.append(ToolMessage(content=_coerce_summary(tool_text), tool_call_id=tc["id"]))
    outputs = {step.output_name: last_text, **_extract_subagent_outputs(last_text)}
    return last_text, outputs


async def run_task(  # noqa: PLR0912, PLR0915 -- protocol assembler; splits would fragment SSE state
    task: SavedTask,
    variables: dict[str, Any],
    *,
    state,
    session_id: str,
    llm: BaseChatModel,
) -> AsyncIterator[str]:
    dto: TaskDTO = to_dto(task)
    msg_id = f"msg_{uuid4().hex}"
    text_id = f"t_{uuid4().hex}"
    yield sse({"type": "start", "messageId": msg_id})
    yield sse({"type": "start-step"})
    yield sse({"type": "text-start", "id": text_id})

    yield _emit_text_delta(text_id, f"Running task **{dto.title}** ({len(dto.steps)} steps).\n\n")

    all_tools = await _all_tools(state)
    tools_by_key: dict[tuple[str | None, str], BaseTool] = {}
    for t in all_tools:
        tools_by_key[(None, t.name)] = t

    outputs: dict[str, dict[str, Any]] = {}
    failed = False
    for step_dto in dto.steps:
        step = step_dto
        step_id = step.id
        yield _emit_input_start(step_id, step.title or step.kind)
        try:
            args_template = step.args_template or {}
            resolved_args = substitute(args_template, variables, outputs) if args_template else {}
            resolved_code = substitute(step.code, variables, outputs) if step.code else None
            resolved_prompt = (
                substitute(step.prompt, variables, outputs) if step.prompt else None
            )

            display_input: dict[str, Any] = {"kind": step.kind, "title": step.title}
            if step.kind == "tool":
                display_input |= {
                    "server": step.server,
                    "tool": step.tool,
                    "args": resolved_args,
                }
            elif step.kind == "code":
                display_input |= {"code": resolved_code}
            elif step.kind == "subagent":
                display_input |= {
                    "subagent": step.subagent,
                    "prompt": resolved_prompt,
                }
            elif step.kind == "prompt":
                display_input |= {"prompt": resolved_prompt}

            yield _emit_input(step_id, step.title or step.kind, display_input)

            if step.kind == "tool":
                summary, step_outputs = await _run_tool_step(
                    step,
                    resolved_args if isinstance(resolved_args, dict) else {},
                    tools_by_key=tools_by_key,
                    session_id=session_id,
                )
            elif step.kind == "code":
                summary, step_outputs = await _run_code_step(
                    step, resolved_code or "", session_id=session_id
                )
            elif step.kind == "prompt":
                summary, step_outputs = await _run_prompt_step(step, resolved_prompt or "", llm=llm)
            elif step.kind == "subagent":
                summary, step_outputs = await _run_subagent_step(
                    step,
                    resolved_prompt or "",
                    llm=llm,
                    all_tools=all_tools,
                    session_id=session_id,
                )
            else:
                raise ValueError(f"unknown step kind {step.kind!r}")  # noqa: TRY301 -- intentional in-loop validation

            outputs[step_id] = step_outputs
            yield _emit_output(step_id, summary)

            for value in step_outputs.values():
                if isinstance(value, dict) and value.get("id") and value.get("kind"):

                    class _Row:
                        def __init__(self, d: dict[str, Any]) -> None:
                            self.id = d["id"]
                            self.kind = d.get("kind", "text")
                            self.title = d.get("title", "Artifact")
                            self.summary = d.get("summary", "")
                            self.updated_at = _now()

                    yield _emit_artifact(step_id, _Row(value))

        except SubstitutionError as e:
            failed = True
            yield _emit_error(step_id, f"variable error: {e}")
            yield _emit_text_delta(text_id, f"\n\nStep `{step.id}` failed: {e}\n")
            break
        except Exception as e:  # noqa: BLE001 -- surface every step failure to UI
            logger.exception(f"task step {step_id} failed")
            failed = True
            yield _emit_error(step_id, str(e))
            yield _emit_text_delta(text_id, f"\n\nStep `{step.id}` failed: {e}\n")
            break

    if not failed:
        yield _emit_text_delta(
            text_id, f"\nDone. {len(outputs)}/{len(dto.steps)} steps completed.\n"
        )

    yield sse({"type": "text-end", "id": text_id})
    yield sse({"type": "finish-step"})
    yield sse({"type": "finish"})
    yield "data: [DONE]\n\n"


def format_run_summary(task: SavedTask, variables: dict[str, Any]) -> str:
    args_str = ", ".join(f"{k}={v!r}" for k, v in variables.items()) or "no variables"
    return f"Run task **{task.title}** ({args_str})"


async def persist_run_messages(
    *,
    session_id: str,
    task: SavedTask,
    variables: dict[str, Any],
) -> None:
    """Insert synthetic user/assistant rows so /sessions list shows the run."""
    async with async_session() as s:
        if not await s.get(ChatSession, session_id):
            s.add(ChatSession(id=session_id, title=f"Task: {task.title}"))
        s.add(
            ChatMessage(
                session_id=session_id,
                role="user",
                content=format_run_summary(task, variables),
            )
        )
        s.add(
            ChatMessage(
                session_id=session_id,
                role="assistant",
                content=json.dumps({"task_id": task.id, "variables": variables}, default=str),
            )
        )
        await s.commit()
