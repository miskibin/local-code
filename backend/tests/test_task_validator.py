from __future__ import annotations

from app.tasks.schemas import TaskDTO, TaskStep, TaskVariable
from app.tasks.validator import has_blocking_issues, validate_task


def _dto(steps: list[TaskStep], **kw) -> TaskDTO:
    return TaskDTO(id="t1", title="t", steps=steps, **kw)


def test_happy_path_no_issues():
    dto = _dto(
        [
            TaskStep(
                id="s1",
                kind="code",
                title="prep",
                code="x = 1",
                output_name="prep",
            ),
            TaskStep(
                id="s2",
                kind="code",
                title="use",
                code="y = read_artifact('{{s1.artifact_id}}')",
                output_name="use",
            ),
        ]
    )
    issues = validate_task(dto, known_tool_names=set())
    assert issues == []
    assert not has_blocking_issues(issues)


def test_duplicate_step_ids():
    dto = _dto(
        [
            TaskStep(id="s1", kind="code", title="a", code="x=1"),
            TaskStep(id="s1", kind="code", title="b", code="y=2"),
        ]
    )
    issues = validate_task(dto, known_tool_names=set())
    assert any(i.field == "id" and "duplicate" in i.message for i in issues)
    assert has_blocking_issues(issues)


def test_forward_ref_blocks():
    dto = _dto(
        [
            TaskStep(
                id="s1",
                kind="code",
                title="a",
                code="x = {{s2.artifact_id}}",
                output_name="a",
            ),
            TaskStep(id="s2", kind="code", title="b", code="y=2", output_name="b"),
        ]
    )
    issues = validate_task(dto, known_tool_names=set())
    assert any("not defined earlier" in i.message for i in issues)
    assert has_blocking_issues(issues)


def test_undefined_variable():
    dto = _dto(
        [
            TaskStep(
                id="s1",
                kind="code",
                title="a",
                code="x = '{{var.missing}}'",
            ),
        ],
        variables=[TaskVariable(name="present")],
    )
    issues = validate_task(dto, known_tool_names=set())
    assert any("unknown variable" in i.message for i in issues)


def test_unknown_step_output_field():
    dto = _dto(
        [
            TaskStep(id="s1", kind="code", title="a", code="x=1", output_name="rows"),
            TaskStep(
                id="s2",
                kind="code",
                title="b",
                code="y = {{s1.foo}}",
            ),
        ]
    )
    issues = validate_task(dto, known_tool_names=set())
    assert any("has no output 'foo'" in i.message for i in issues)


def test_builtin_step_field_artifact_id_is_ok():
    dto = _dto(
        [
            TaskStep(id="s1", kind="code", title="a", code="x=1"),
            TaskStep(
                id="s2",
                kind="code",
                title="b",
                code="y = read_artifact('{{s1.artifact_id}}')",
            ),
        ]
    )
    issues = validate_task(dto, known_tool_names=set())
    assert issues == []


def test_unknown_tool_is_warning_not_error():
    dto = _dto(
        [
            TaskStep(id="s1", kind="tool", title="a", tool="some_mcp_tool"),
        ]
    )
    issues = validate_task(dto, known_tool_names={"sql_query"})
    assert any(i.severity == "warning" and i.field == "tool" for i in issues)
    assert not has_blocking_issues(issues)


def test_known_tool_passes():
    dto = _dto(
        [
            TaskStep(id="s1", kind="tool", title="a", tool="sql_query"),
        ]
    )
    issues = validate_task(dto, known_tool_names={"sql_query"})
    assert issues == []


def test_code_syntax_error():
    dto = _dto(
        [
            TaskStep(id="s1", kind="code", title="a", code="x = (\n"),
        ]
    )
    issues = validate_task(dto, known_tool_names=set())
    assert any(i.field == "code" and "syntax error" in i.message for i in issues)
    assert has_blocking_issues(issues)


def test_unknown_subagent_blocks():
    dto = _dto(
        [
            TaskStep(
                id="s1",
                kind="subagent",
                title="a",
                subagent="nonexistent-agent",
                prompt="do thing",
            ),
        ]
    )
    issues = validate_task(dto, known_tool_names=set())
    assert any(i.field == "subagent" and "unknown subagent" in i.message for i in issues)


def test_known_subagent_passes():
    dto = _dto(
        [
            TaskStep(
                id="s1",
                kind="subagent",
                title="a",
                subagent="sql-agent",
                prompt="do thing",
            ),
        ]
    )
    issues = validate_task(dto, known_tool_names=set())
    assert issues == []


def test_empty_code_step_blocks():
    dto = _dto(
        [
            TaskStep(id="s1", kind="code", title="a", code=""),
        ]
    )
    issues = validate_task(dto, known_tool_names=set())
    assert any(i.field == "code" and "non-empty" in i.message for i in issues)


def test_tool_step_missing_tool_name():
    dto = _dto(
        [
            TaskStep(id="s1", kind="tool", title="a"),
        ]
    )
    issues = validate_task(dto, known_tool_names=set())
    assert any(i.field == "tool" and "requires a tool name" in i.message for i in issues)


def test_unused_output_warns_when_downstream_hardcodes_value():
    """Mirrors the Track-task bug: s2 filters columns, s3 SQL hardcodes the result."""
    dto = _dto(
        [
            TaskStep(
                id="s1",
                kind="subagent",
                title="List columns",
                subagent="sql-agent",
                prompt="List columns of {{var.table}}",
                output_name="cols",
            ),
            TaskStep(
                id="s2",
                kind="code",
                title="Filter",
                code="out([c for c in ['GenreId','Name'] if 'g' in c.lower()])",
                output_name="filtered",
            ),
            TaskStep(
                id="s3",
                kind="tool",
                title="Count",
                tool="sql_query",
                args_template={"sql": "SELECT COUNT(*) FROM Track WHERE GenreId IS NOT NULL"},
                output_name="row_count",
            ),
        ],
        variables=[TaskVariable(name="table")],
    )
    issues = validate_task(dto, known_tool_names={"sql_query"})
    warnings = [i for i in issues if i.severity == "warning"]
    assert any(i.step_id == "s2" and "filtered" in i.message for i in warnings)
    assert not has_blocking_issues(issues)


def test_unused_output_clean_when_downstream_references_it():
    dto = _dto(
        [
            TaskStep(
                id="s1",
                kind="subagent",
                title="List",
                subagent="sql-agent",
                prompt="List columns of {{var.table}}",
                output_name="cols",
            ),
            TaskStep(
                id="s2",
                kind="code",
                title="Filter",
                code="out_sql_list([c for c in ['GenreId'] if 'g' in c.lower()])",
                output_name="filtered",
            ),
            TaskStep(
                id="s3",
                kind="tool",
                title="Count",
                tool="sql_query",
                args_template={
                    "sql": "SELECT COUNT(*) FROM Track WHERE {{s2.filtered}} IS NOT NULL"
                },
                output_name="row_count",
            ),
        ],
        variables=[TaskVariable(name="table")],
    )
    issues = validate_task(dto, known_tool_names={"sql_query"})
    assert not any(
        i.severity == "warning" and i.step_id == "s2" and "filtered" in i.message for i in issues
    )


def test_unused_output_excludes_report_consumption():
    """Auto-generated report steps reference every prior step's artifact_id for
    display only — they must NOT count as a real consumer."""
    dto = _dto(
        [
            TaskStep(
                id="s1",
                kind="code",
                title="Build",
                code="out([{'a': 1}])",
                output_name="rows",
            ),
            TaskStep(
                id="s2",
                kind="tool",
                title="Hardcoded",
                tool="sql_query",
                args_template={"sql": "SELECT 1"},
                output_name="x",
            ),
            TaskStep(
                id="s3",
                kind="report",
                title="Results",
                prompt="[s1](artifact:{{s1.artifact_id}})\n[s2](artifact:{{s2.artifact_id}})",
                output_name="report",
            ),
        ]
    )
    issues = validate_task(dto, known_tool_names={"sql_query"})
    warnings = [i for i in issues if i.severity == "warning"]
    assert any(i.step_id == "s1" for i in warnings)


def test_unused_output_skips_last_step():
    """The last non-report step has no possible consumer — silently OK."""
    dto = _dto(
        [
            TaskStep(
                id="s1",
                kind="code",
                title="Only",
                code="out([{'a': 1}])",
                output_name="rows",
            ),
        ]
    )
    issues = validate_task(dto, known_tool_names=set())
    assert issues == []


def test_unused_output_does_not_flag_report_step():
    dto = _dto(
        [
            TaskStep(
                id="s1",
                kind="code",
                title="Build",
                code="out([{'a': 1}])",
                output_name="rows",
            ),
            TaskStep(
                id="s2",
                kind="code",
                title="Use",
                code="x = {{s1.rows}}",
                output_name="used",
            ),
            TaskStep(
                id="s3",
                kind="report",
                title="Results",
                prompt="done",
                output_name="report",
            ),
        ]
    )
    issues = validate_task(dto, known_tool_names=set())
    assert not any(i.severity == "warning" and i.step_id == "s3" for i in issues)


def test_real_failure_task_passes_validator_by_design():
    """The Invoice task that triggered this work — semantic, not structural.

    Validator does NOT catch it (s1's SQL returns wrong shape). Asserting that
    keeps the scope honest.
    """
    dto = _dto(
        [
            TaskStep(
                id="s1",
                kind="tool",
                title="Extract",
                tool="sql_query",
                args_template={"sql": "SELECT sql FROM sqlite_master WHERE type='table';"},
                output_name="dataset",
            ),
            TaskStep(
                id="s2",
                kind="code",
                title="Train",
                code="df = read_artifact('{{s1.artifact_id}}')\ndf['Country']",
                output_name="importances",
            ),
        ]
    )
    issues = validate_task(dto, known_tool_names={"sql_query"})
    assert not has_blocking_issues(issues)
