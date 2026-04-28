"""Static validation for saved tasks at create / update time.

No dry-run, no LLM. Catches structural/syntactic problems only:
duplicate ids, broken {{...}} refs, unknown tool/subagent names,
syntax errors in code blocks. Semantic mismatches (s1 returned
columns A,B but s2 reads C) are out of scope by design.
"""

from __future__ import annotations

import ast
import re

from app.graphs.main_agent import default_subagents
from app.tasks.schemas import TaskDTO, TaskStep, ValidationIssue
from app.tool_registry import discover_tools

_REF_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")
_BUILTIN_STEP_FIELDS = frozenset({"artifact_id", "text", "rows", "columns"})
_REPORT_REF_FIELDS = frozenset({"artifact_id"})


def _refs_in(value: object) -> list[str]:
    out: list[str] = []
    if isinstance(value, str):
        out.extend(m.group(1) for m in _REF_RE.finditer(value))
    elif isinstance(value, dict):
        for v in value.values():
            out.extend(_refs_in(v))
    elif isinstance(value, list):
        for v in value:
            out.extend(_refs_in(v))
    return out


def _check_ref(
    ref: str,
    *,
    step: TaskStep,
    field: str,
    var_names: set[str],
    earlier_outputs: dict[str, set[str]],
) -> ValidationIssue | None:
    head, sep, tail = ref.partition(".")
    if not sep:
        return ValidationIssue(
            severity="error",
            step_id=step.id,
            field=field,
            message=f"reference {{{{{ref}}}}} must be {{{{var.X}}}} or {{{{stepId.X}}}}",
        )
    if head == "var":
        if tail not in var_names:
            return ValidationIssue(
                severity="error",
                step_id=step.id,
                field=field,
                message=f"unknown variable {tail!r} in {{{{{ref}}}}}",
            )
        return None
    available = earlier_outputs.get(head)
    if available is None:
        return ValidationIssue(
            severity="error",
            step_id=step.id,
            field=field,
            message=f"reference to step {head!r} which is not defined earlier",
        )
    if tail not in available and tail not in _BUILTIN_STEP_FIELDS:
        avail = ", ".join(sorted(available | _BUILTIN_STEP_FIELDS))
        return ValidationIssue(
            severity="error",
            step_id=step.id,
            field=field,
            message=f"step {head!r} has no output {tail!r} (available: {avail})",
        )
    return None


def validate_task(  # noqa: PLR0912 -- straight-line per-kind branch list; splits would fragment
    dto: TaskDTO,
    *,
    known_tool_names: set[str] | None = None,
) -> list[ValidationIssue]:
    """Run all checks, collect every issue. Caller decides what severity blocks."""
    issues: list[ValidationIssue] = []

    if known_tool_names is None:
        known_tool_names = {t.name for t in discover_tools()}
    known_subagents = {s["name"] for s in default_subagents()}
    var_names = {v.name for v in dto.variables}

    seen_ids: set[str] = set()
    for step in dto.steps:
        if step.id in seen_ids:
            issues.append(
                ValidationIssue(
                    severity="error",
                    step_id=step.id,
                    field="id",
                    message=f"duplicate step id {step.id!r}",
                )
            )
        seen_ids.add(step.id)

    earlier_outputs: dict[str, set[str]] = {}
    for step in dto.steps:
        for field, value in (
            ("args_template", step.args_template),
            ("code", step.code),
            ("prompt", step.prompt),
        ):
            for ref in _refs_in(value):
                issue = _check_ref(
                    ref,
                    step=step,
                    field=field,
                    var_names=var_names,
                    earlier_outputs=earlier_outputs,
                )
                if issue is not None:
                    issues.append(issue)

        if step.kind == "tool":
            if not step.tool:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        step_id=step.id,
                        field="tool",
                        message="tool step requires a tool name",
                    )
                )
            elif step.tool not in known_tool_names:
                # MCP tools hot-reload, so unknown name is a warning not an
                # error — local discovery may not see currently-loaded MCP tools.
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        step_id=step.id,
                        field="tool",
                        message=(
                            f"tool {step.tool!r} not in local registry "
                            "(may be an MCP tool loaded at runtime)"
                        ),
                    )
                )
        elif step.kind == "code":
            if not step.code:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        step_id=step.id,
                        field="code",
                        message="code step requires non-empty code",
                    )
                )
            else:
                try:
                    ast.parse(step.code)
                except SyntaxError as e:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            step_id=step.id,
                            field="code",
                            message=f"syntax error at line {e.lineno}: {e.msg}",
                        )
                    )
        elif step.kind == "subagent":
            if not step.prompt:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        step_id=step.id,
                        field="prompt",
                        message="subagent step requires a prompt",
                    )
                )
            if step.subagent and step.subagent not in known_subagents:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        step_id=step.id,
                        field="subagent",
                        message=(
                            f"unknown subagent {step.subagent!r}; "
                            f"have: {', '.join(sorted(known_subagents))}"
                        ),
                    )
                )
        elif step.kind == "prompt":
            if not step.prompt:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        step_id=step.id,
                        field="prompt",
                        message="prompt step requires non-empty prompt",
                    )
                )
        elif step.kind == "report" and not step.prompt:
            issues.append(
                ValidationIssue(
                    severity="error",
                    step_id=step.id,
                    field="prompt",
                    message="report step requires a prompt template",
                )
            )

        # Register this step's outputs for later refs.
        earlier_outputs[step.id] = {step.output_name}

    issues.extend(_unused_output_warnings(dto))
    return issues


def _step_refs(step: TaskStep) -> list[str]:
    """All {{...}} references inside a step's content fields."""
    refs: list[str] = []
    for value in (step.args_template, step.code, step.prompt):
        refs.extend(_refs_in(value))
    return refs


def _unused_output_warnings(dto: TaskDTO) -> list[ValidationIssue]:
    """Warn when a non-report step's output is never consumed by a later
    non-report step.

    Why this matters: tasks generated from a single run sometimes leave a
    `code`/`subagent` step whose output (e.g. a filtered column list) is
    purely informational while a downstream `tool` step has the relevant
    value hardcoded into its `args_template`. Re-running the task with
    different inputs silently yields stale results because the downstream
    step never reads the upstream output. Auto-generated `report` steps
    reference every prior step via `artifact_id` for display, so they are
    excluded from "consumer" detection.
    """
    out: list[ValidationIssue] = []
    consumer_steps = [s for s in dto.steps if s.kind != "report"]
    for i, step in enumerate(consumer_steps):
        if step.kind == "report":
            continue
        prefix = f"{step.id}."
        consumed = any(
            any(r.startswith(prefix) for r in _step_refs(later))
            for later in consumer_steps[i + 1 :]
        )
        if consumed:
            continue
        # Last non-report step has no possible consumer — skip silently.
        if i == len(consumer_steps) - 1:
            continue
        out.append(
            ValidationIssue(
                severity="warning",
                step_id=step.id,
                field=None,
                message=(
                    f"step output {step.output_name!r} is not referenced by any "
                    f"later step — downstream steps may have hardcoded values "
                    f"that go stale as data changes"
                ),
            )
        )
    return out


def has_blocking_issues(issues: list[ValidationIssue]) -> bool:
    return any(i.severity == "error" for i in issues)
