"""Hybrid task runner.

TOOL/CODE steps run scripted (direct tool/python_exec invocation).
SUBAGENT/PROMPT steps run through an LLM call (with optional tool binding).

All steps emit SSE events that match the chat tool-call protocol bit-for-bit
so the frontend renders them through the same per-tool renderers as ordinary
chat tool calls. Step title rides along as `providerMetadata.task.title`.
On any step failure we halt and surface the error — no retry, no skip.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState
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
from app.tasks import coerce_lc_content
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


async def _all_tools(state) -> list[BaseTool]:
    local = tool_registry.discover_tools()
    mcp = state.mcp_registry.tools if hasattr(state, "mcp_registry") else []
    return local + mcp


def _task_md(step: TaskStep) -> dict:
    return {"task": {"stepId": step.id, "title": step.title, "kind": step.kind}}


def _subagent_md(step: TaskStep) -> dict:
    return {
        "subagent": {
            "namespace": [f"task:{step.id}"],
            "parentToolCallId": step.id,
        }
    }


def _emit_text_delta(text_id: str, delta: str) -> str:
    return sse({"type": "text-delta", "id": text_id, "delta": delta})


def _emit_input_start(call_id: str, name: str, *, provider_md: dict | None = None) -> str:
    evt: dict = {"type": "tool-input-start", "toolCallId": call_id, "toolName": name}
    if provider_md:
        evt["providerMetadata"] = provider_md
    return sse(evt)


def _emit_input(call_id: str, name: str, args: object, *, provider_md: dict | None = None) -> str:
    evt: dict = {
        "type": "tool-input-available",
        "toolCallId": call_id,
        "toolName": name,
        "input": args,
    }
    if provider_md:
        evt["providerMetadata"] = provider_md
    return sse(evt)


def _emit_output(call_id: str, output: object, *, provider_md: dict | None = None) -> str:
    evt: dict = {"type": "tool-output-available", "toolCallId": call_id, "output": output}
    if provider_md:
        evt["providerMetadata"] = provider_md
    return sse(evt)


def _emit_error(call_id: str, error_text: str, *, provider_md: dict | None = None) -> str:
    evt: dict = {"type": "tool-output-error", "toolCallId": call_id, "errorText": error_text}
    if provider_md:
        evt["providerMetadata"] = provider_md
    return sse(evt)


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
    summary_text = coerce_lc_content(summary)
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
) -> tuple[str, dict[str, Any]]:
    if not prompt:
        raise ValueError(f"step {step.id}: prompt required for kind=prompt")
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    text = coerce_lc_content(getattr(response, "content", response))
    return text, {step.output_name: text}


async def _run_subagent_step(
    step: TaskStep,
    prompt: str,
    *,
    llm: BaseChatModel,
    all_tools: list[BaseTool],
    session_id: str,
) -> AsyncIterator[str | tuple[str, dict[str, Any]]]:
    """Run a subagent ReAct loop, yielding SSE strings for each inner tool call.

    Final yield is a `(summary, outputs)` tuple — the caller forwards SSE
    strings to the client and uses the tuple to populate the dispatcher
    output event and outputs map.
    """
    if not prompt:
        raise ValueError(f"step {step.id}: prompt required for kind=subagent")
    target = step.subagent or ""
    spec = next((s for s in default_subagents() if s["name"] == target), None)
    system = spec["system_prompt"] if spec else "You are a helpful sub-agent."
    tool_names: list[str] = list(spec.get("tools", [])) if spec else []
    bound_tools = [t for t in all_tools if t.name in tool_names]
    chain = llm.bind_tools(bound_tools) if bound_tools else llm

    sub_md = _subagent_md(step)
    messages: list[Any] = [HumanMessage(content=f"{system}\n\n{prompt}")]
    last_text = ""
    for _ in range(4):  # cap subagent ReAct loop to keep tasks deterministic-ish
        response = await chain.ainvoke(messages)
        messages.append(response)
        text = coerce_lc_content(getattr(response, "content", response))
        last_text = text or last_text
        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            break
        config = {"configurable": {"thread_id": session_id}}
        for tc in tool_calls:
            inner_id = tc.get("id") or f"sa_{uuid4().hex}"
            inner_name = tc["name"]
            inner_args = tc.get("args") or {}
            yield _emit_input_start(inner_id, inner_name, provider_md=sub_md)
            yield _emit_input(inner_id, inner_name, inner_args, provider_md=sub_md)
            tool = next((t for t in bound_tools if t.name == inner_name), None)
            if tool is None:
                err_text = f"tool {inner_name} not bound"
                yield _emit_error(inner_id, err_text, provider_md=sub_md)
                messages.append(ToolMessage(content=err_text, tool_call_id=inner_id))
                continue
            raw = await tool.ainvoke(inner_args, config=config)
            if isinstance(raw, tuple) and len(raw) == _CONTENT_AND_ARTIFACT_LEN:
                tool_text, _ = raw
            else:
                tool_text = raw
            tool_text_str = coerce_lc_content(tool_text)
            yield _emit_output(inner_id, tool_text_str, provider_md=sub_md)
            messages.append(ToolMessage(content=tool_text_str, tool_call_id=inner_id))
    outputs = {step.output_name: last_text, **_extract_subagent_outputs(last_text)}
    yield (last_text, outputs)


async def run_task(  # noqa: PLR0912, PLR0915 -- protocol assembler; splits would fragment SSE state
    task: SavedTask,
    variables: dict[str, Any],
    *,
    state,
    session_id: str,
    llm: BaseChatModel,
    lc_messages: list | None = None,
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

    ai_tool_calls: list[dict[str, Any]] = []
    pending_tool_msgs: list[ToolMessage] = []
    prompt_texts: list[str] = []
    if lc_messages is not None:
        lc_messages.append(HumanMessage(content=format_run_summary(task, variables)))

    outputs: dict[str, dict[str, Any]] = {}
    failed = False
    for step_dto in dto.steps:
        step = step_dto
        step_id = step.id
        task_md = _task_md(step)

        try:
            args_template = step.args_template or {}
            resolved_args = substitute(args_template, variables, outputs) if args_template else {}
            resolved_code = substitute(step.code, variables, outputs) if step.code else None
            resolved_prompt = substitute(step.prompt, variables, outputs) if step.prompt else None

            if step.kind == "tool":
                tool_name = step.tool or step.kind
                args_dict = resolved_args if isinstance(resolved_args, dict) else {}
                yield _emit_input_start(step_id, tool_name, provider_md=task_md)
                yield _emit_input(step_id, tool_name, args_dict, provider_md=task_md)
                summary, step_outputs = await _run_tool_step(
                    step, args_dict, tools_by_key=tools_by_key, session_id=session_id
                )
                yield _emit_output(step_id, summary, provider_md=task_md)
                ai_tool_calls.append({"id": step_id, "name": tool_name, "args": args_dict})
                pending_tool_msgs.append(ToolMessage(content=summary, tool_call_id=step_id))

            elif step.kind == "code":
                code_str = resolved_code or ""
                yield _emit_input_start(step_id, "python_exec", provider_md=task_md)
                yield _emit_input(step_id, "python_exec", {"code": code_str}, provider_md=task_md)
                summary, step_outputs = await _run_code_step(step, code_str, session_id=session_id)
                yield _emit_output(step_id, summary, provider_md=task_md)
                ai_tool_calls.append(
                    {"id": step_id, "name": "python_exec", "args": {"code": code_str}}
                )
                pending_tool_msgs.append(ToolMessage(content=summary, tool_call_id=step_id))

            elif step.kind == "subagent":
                dispatch_input = {
                    "subagent_type": step.subagent or "",
                    "description": step.title or (step.prompt or "")[:80],
                }
                yield _emit_input_start(step_id, "task", provider_md=task_md)
                yield _emit_input(step_id, "task", dispatch_input, provider_md=task_md)
                summary = ""
                step_outputs = {}
                async for evt in _run_subagent_step(
                    step,
                    resolved_prompt or "",
                    llm=llm,
                    all_tools=all_tools,
                    session_id=session_id,
                ):
                    if isinstance(evt, str):
                        yield evt
                    else:
                        summary, step_outputs = evt
                yield _emit_output(step_id, summary, provider_md=task_md)
                ai_tool_calls.append({"id": step_id, "name": "task", "args": dispatch_input})
                pending_tool_msgs.append(ToolMessage(content=summary, tool_call_id=step_id))

            elif step.kind == "prompt":
                yield _emit_text_delta(text_id, f"\n**{step.title}**\n\n")
                summary, step_outputs = await _run_prompt_step(step, resolved_prompt or "", llm=llm)
                yield _emit_text_delta(text_id, summary)
                yield _emit_text_delta(text_id, "\n\n")
                prompt_texts.append(f"**{step.title}**\n\n{summary}")

            else:
                raise ValueError(f"unknown step kind {step.kind!r}")  # noqa: TRY301 -- intentional in-loop validation

            outputs[step_id] = step_outputs

            for value in step_outputs.values():
                if isinstance(value, dict) and value.get("id") and value.get("kind"):
                    yield _emit_artifact(
                        step_id,
                        SimpleNamespace(
                            id=value["id"],
                            kind=value.get("kind", "text"),
                            title=value.get("title", "Artifact"),
                            summary=value.get("summary", ""),
                            updated_at=datetime.now(UTC),
                        ),
                    )

        except SubstitutionError as e:
            failed = True
            yield _emit_error(step_id, f"variable error: {e}", provider_md=task_md)
            yield _emit_text_delta(text_id, f"\n\nStep `{step.id}` failed: {e}\n")
            ai_tool_calls.append({"id": step_id, "name": step.tool or step.kind, "args": {}})
            pending_tool_msgs.append(
                ToolMessage(content=f"variable error: {e}", tool_call_id=step_id, status="error")
            )
            break
        except Exception as e:  # noqa: BLE001 -- surface every step failure to UI
            logger.exception(f"task step {step_id} failed")
            failed = True
            yield _emit_error(step_id, str(e), provider_md=task_md)
            yield _emit_text_delta(text_id, f"\n\nStep `{step.id}` failed: {e}\n")
            ai_tool_calls.append({"id": step_id, "name": step.tool or step.kind, "args": {}})
            pending_tool_msgs.append(
                ToolMessage(content=str(e), tool_call_id=step_id, status="error")
            )
            break

    if not failed:
        yield _emit_text_delta(
            text_id, f"\nDone. {len(outputs)}/{len(dto.steps)} steps completed.\n"
        )

    if lc_messages is not None:
        ai_content = (
            "\n\n".join(prompt_texts) if prompt_texts else ("ok" if not failed else "failed")
        )
        lc_messages.append(AIMessage(id=msg_id, content=ai_content, tool_calls=ai_tool_calls))
        lc_messages.extend(pending_tool_msgs)

    yield sse({"type": "text-end", "id": text_id})
    yield sse({"type": "finish-step"})
    yield sse({"type": "finish"})
    yield "data: [DONE]\n\n"


async def persist_task_run_checkpoint(checkpointer, session_id: str, lc_msgs: list) -> None:
    """Append LC messages to thread session_id via the shared checkpointer.

    Compiles a tiny passthrough MessagesState graph per call — compilation is
    microseconds, and caching across tests/app instances would bind to a stale
    checkpointer.
    """
    if not lc_msgs:
        return
    g = StateGraph(MessagesState)
    g.add_node("p", lambda _s: {})
    g.add_edge(START, "p")
    g.add_edge("p", END)
    graph = g.compile(checkpointer=checkpointer)
    await graph.ainvoke(
        {"messages": lc_msgs},
        config={"configurable": {"thread_id": session_id}},
    )


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
