"""Variable + prior-step output substitution for task runner.

Syntax:
    {{var.name}}            -> user-supplied variable value
    {{stepId.output_name}}  -> output produced by an earlier step in the same run

Rules:
    - Walk dict / list / str values recursively.
    - If a string is exactly a single {{...}} reference, replace with the raw
      referenced value (preserves objects).
    - Otherwise do plain text interpolation (str() of each ref).
    - Unresolved reference raises SubstitutionError before the step runs.
"""

from __future__ import annotations

import re
from typing import Any

_REF_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")
_FULL_RE = re.compile(r"^\s*\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}\s*$")


class SubstitutionError(ValueError):
    """Raised when a {{...}} reference cannot be resolved."""


def _lookup(
    ref: str,
    variables: dict[str, Any],
    outputs: dict[str, dict[str, Any]],
) -> Any:
    head, sep, tail = ref.partition(".")
    if not sep:
        raise SubstitutionError(
            f"reference {ref!r} must be {{{{var.<name>}}}} or {{{{<stepId>.<output>}}}}"
        )
    if head == "var":
        if tail not in variables:
            raise SubstitutionError(f"variable {tail!r} not provided")
        return variables[tail]
    step_outputs = outputs.get(head)
    if step_outputs is None:
        raise SubstitutionError(f"step {head!r} has not run yet")
    if tail not in step_outputs:
        available = ", ".join(sorted(step_outputs)) or "(none)"
        raise SubstitutionError(
            f"step {head!r} did not produce output {tail!r} (have: {available})"
        )
    return step_outputs[tail]


def _stringify(value: Any) -> str:
    """Convert a looked-up value to its string form for inline interpolation.

    Code steps store their full artifact dict under output_name so that the
    runner's artifact-emit loop can pick it up. When that dict is interpolated
    into a string template (e.g. SQL inside args_template), the useful payload
    is the text/rows, not the wrapper. Unwrap text artifacts to their `text`
    field — that's what `out_sql_list` and friends are designed to feed.
    """
    if (
        isinstance(value, dict)
        and value.get("kind") == "text"
        and isinstance(value.get("payload"), dict)
    ):
        return str(value["payload"].get("text", ""))
    return str(value)


def substitute(
    value: Any,
    variables: dict[str, Any],
    outputs: dict[str, dict[str, Any]],
) -> Any:
    if isinstance(value, str):
        full = _FULL_RE.match(value)
        if full:
            return _lookup(full.group(1), variables, outputs)

        def repl(m: re.Match[str]) -> str:
            return _stringify(_lookup(m.group(1), variables, outputs))

        return _REF_RE.sub(repl, value)
    if isinstance(value, list):
        return [substitute(v, variables, outputs) for v in value]
    if isinstance(value, dict):
        return {k: substitute(v, variables, outputs) for k, v in value.items()}
    return value
