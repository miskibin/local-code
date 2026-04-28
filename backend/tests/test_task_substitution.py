import pytest

from app.tasks.substitution import SubstitutionError, substitute


def test_substitute_var_in_string():
    out = substitute("hello {{var.name}}", variables={"name": "world"}, outputs={})
    assert out == "hello world"


def test_substitute_full_string_returns_raw_object():
    rows = [{"a": 1}, {"a": 2}]
    out = substitute(
        "{{s1.rows}}",
        variables={},
        outputs={"s1": {"rows": rows}},
    )
    assert out is rows


def test_substitute_nested_dict_and_list():
    out = substitute(
        {"path": "{{var.dir}}/file.csv", "rows": ["{{s1.row}}"]},
        variables={"dir": "/data"},
        outputs={"s1": {"row": {"id": 1}}},
    )
    assert out == {"path": "/data/file.csv", "rows": [{"id": 1}]}


def test_substitute_unknown_variable_raises():
    with pytest.raises(SubstitutionError):
        substitute("{{var.missing}}", variables={}, outputs={})


def test_substitute_bare_ref_without_dot_raises():
    with pytest.raises(SubstitutionError):
        substitute("{{name}}", variables={"name": "x"}, outputs={})


def test_substitute_unknown_step_output_raises():
    with pytest.raises(SubstitutionError):
        substitute(
            "{{s1.missing}}",
            variables={},
            outputs={"s1": {"rows": []}},
        )


def test_substitute_passthrough_for_non_template_strings():
    assert substitute("plain text", {}, {}) == "plain text"
    assert substitute(42, {}, {}) == 42
    assert substitute(None, {}, {}) is None


def test_substitute_unwraps_text_artifact_for_inline_interpolation():
    """A code step's output is the artifact dict; inline interpolation (used
    e.g. for SQL fragments produced by `out_sql_list`) must unwrap to the
    payload text instead of stringifying the dict wrapper."""
    artifact = {
        "id": "art_x",
        "kind": "text",
        "title": "Python output",
        "payload": {"text": "'GenreId', 'AlbumId'", "stderr": None},
        "summary": "...",
    }
    out = substitute(
        {"sql": "SELECT * FROM t WHERE col IN ({{s1.filtered}})"},
        variables={},
        outputs={"s1": {"filtered": artifact, "artifact_id": "art_x"}},
    )
    assert out == {"sql": "SELECT * FROM t WHERE col IN ('GenreId', 'AlbumId')"}


def test_substitute_full_ref_keeps_artifact_dict():
    """Full {{...}} ref keeps the raw value — needed for tools that consume
    the artifact dict directly."""
    artifact = {"id": "art_x", "kind": "text", "payload": {"text": "hi"}}
    out = substitute(
        "{{s1.x}}",
        variables={},
        outputs={"s1": {"x": artifact}},
    )
    assert out is artifact
