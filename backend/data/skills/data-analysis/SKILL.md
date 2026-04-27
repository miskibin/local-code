---
name: data-analysis
description: Methodology recipes for multi-step data questions over the bundled DB. Load when the user asks for a complex breakdown, comparison, or anything that needs more than one SQL pass.
---

# Data analysis recipes

The core rules (delegating to sql-agent, parsing the artifact-id contract,
artifact visibility) are already in your main instructions — this skill
only contains extra patterns for non-trivial questions.

## Picking a dimension when the user is vague

If the user says "show me trends" or "what's interesting in the data",
pick a dimension yourself rather than asking back. Default options for the
Chinook DB:

- **time** — invoice date by month/quarter; good for trend questions
- **geography** — billing country; good when user mentions regions
- **genre / artist** — when user mentions music
- **customer** — when user mentions revenue / spend

Pick the dimension that gives the cleanest story. State the dimension you
picked in the first line of your reply.

## Multi-step delegation pattern

For questions that need two or more SQL passes (e.g. "top 10 X then break
each by Y"):

1. First `task(subagent_type="sql-agent", description=...)` for the
   filter/seed list. Parse `artifact_id=art_a; columns=...`.
2. Second `task(subagent_type="sql-agent", description=...)` referencing
   the IDs from step 1 explicitly in the description so the sub-agent can
   embed them in a `WHERE … IN (...)` clause.
3. Process / chart in `python_exec`, joining the two artifacts on the
   shared id column.

Never try to do both passes in one SQL call — the sub-agent is allowed
LIMIT 200 and the join can blow past it.

## Validating before you present

Quick sanity checks after `read_artifact`:

- Row count matches the LIMIT you asked for, or the question intent.
- Numeric totals are plausible (no all-zero, no unexpected negatives).
- No mostly-null columns.

If something looks off, refine via another `sql-agent` call rather than
papering over it in pandas.
