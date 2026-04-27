"""Pin the SQL-subagent's final-line exit contract.

The system prompt for `sql-agent` (`backend/app/graphs/main_agent.py:90-94`)
mandates the subagent's final reply ends with a line in the exact shape:

    artifact_id=<id>; columns=<csv>

`backend/app/tasks/runner.py:_extract_subagent_outputs` (lines 47-62) parses
that line into structured outputs the parent task can reference via template
substitution (`{{stepId.artifact_id}}`, `{{stepId.columns}}`). If the regexes
drift, the parent silently sees `None` for both — no error, just broken
chaining.

Pin the parser across:
- the canonical happy path,
- realistic negative shapes (missing fields, malformed columns, code fences,
  whitespace),
- multiline final reply (line is somewhere in the middle/end of the text).
"""

from __future__ import annotations

import pytest

from app.tasks.runner import _extract_subagent_outputs


@pytest.mark.parametrize(
    "text, expected",
    [
        # --- canonical happy paths ---
        (
            "Customers ranked by total spend.\n"
            "artifact_id=art_754c2be1b408; columns=FirstName,LastName,TotalSpend",
            {
                "artifact_id": "art_754c2be1b408",
                "columns": ["FirstName", "LastName", "TotalSpend"],
            },
        ),
        (
            # single-column result
            "artifact_id=art_abc123def456; columns=Year",
            {"artifact_id": "art_abc123def456", "columns": ["Year"]},
        ),
        (
            # extra whitespace around `=` and around column commas
            "artifact_id = art_abc123 ; columns = a, b , c",
            {"artifact_id": "art_abc123", "columns": ["a", "b", "c"]},
        ),
        (
            # the line lives at the end of a multi-paragraph reply
            "Top 10 albums.\n\nThis covers the rock genre only.\n"
            "artifact_id=art_aaaaaaaaaaaa; columns=Title,Artist,UnitPrice",
            {
                "artifact_id": "art_aaaaaaaaaaaa",
                "columns": ["Title", "Artist", "UnitPrice"],
            },
        ),
        # --- negative shapes ---
        (
            # free text with no exit line — both fields absent (NOT KeyError)
            "Here's a summary of customers by country.",
            {},
        ),
        (
            # only artifact_id present (columns missing) — partial extraction
            "artifact_id=art_xxxxxxxxxxxx",
            {"artifact_id": "art_xxxxxxxxxxxx"},
        ),
        (
            # only columns present (artifact_id missing)
            "columns=Foo,Bar",
            {"columns": ["Foo", "Bar"]},
        ),
        (
            # malformed id (no `art_` prefix) — regex must NOT match
            "artifact_id=xyz; columns=Foo",
            {"columns": ["Foo"]},
        ),
        (
            # columns value contains an empty entry from trailing comma —
            # the parser strips empties so the result is just the real names
            "artifact_id=art_aabbccddeeff; columns=A,,B,",
            {"artifact_id": "art_aabbccddeeff", "columns": ["A", "B"]},
        ),
        (
            # empty input
            "",
            {},
        ),
    ],
)
def test_extract_subagent_outputs_parametrized(text, expected):
    assert _extract_subagent_outputs(text) == expected


def test_extract_handles_none_input_gracefully():
    """Defensive: caller passes `text or ""` already, but in case it ever
    passes `None` directly, the parser must not crash."""
    assert _extract_subagent_outputs(None) == {}  # type: ignore[arg-type]


def test_canonical_example_from_system_prompt_parses_cleanly():
    """The literal example in `main_agent.py:92` MUST round-trip — if the
    prompt's example shape ever drifts from the parser's regex, the
    documented contract is broken."""
    example = "artifact_id=art_754c2be1b408; columns=FirstName,LastName,TotalSpend"
    out = _extract_subagent_outputs(example)
    assert out == {
        "artifact_id": "art_754c2be1b408",
        "columns": ["FirstName", "LastName", "TotalSpend"],
    }
