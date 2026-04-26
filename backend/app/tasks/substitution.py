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
    if head == "var":
        if tail not in variables:
            raise SubstitutionError(f"variable {tail!r} not provided")
        return variables[tail]
    # Bare {{name}} — common shorthand from LLM-generated tasks. If it matches
    # a declared variable, resolve as one; otherwise fall through.
    if not sep and head in variables:
        return variables[head]
    if not sep:
        raise SubstitutionError(
            f"reference {head!r} is not a variable; use {{{{var.{head}}}}} or {{{{stepId.output}}}}"
        )
    # Otherwise treat head as a step id, tail as an output name.
    step_outputs = outputs.get(head)
    if step_outputs is None:
        raise SubstitutionError(f"step {head!r} has not run yet")
    if tail not in step_outputs:
        available = ", ".join(sorted(step_outputs)) or "(none)"
        raise SubstitutionError(
            f"step {head!r} did not produce output {tail!r} (have: {available})"
        )
    return step_outputs[tail]


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
            return str(_lookup(m.group(1), variables, outputs))

        return _REF_RE.sub(repl, value)
    if isinstance(value, list):
        return [substitute(v, variables, outputs) for v in value]
    if isinstance(value, dict):
        return {k: substitute(v, variables, outputs) for k, v in value.items()}
    return value
