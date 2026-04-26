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


def test_substitute_bare_var_shorthand_resolves():
    out = substitute(
        "hello {{name}}",
        variables={"name": "world"},
        outputs={},
    )
    assert out == "hello world"


def test_substitute_bare_unknown_ref_raises():
    with pytest.raises(SubstitutionError):
        substitute("{{nope}}", variables={"x": 1}, outputs={})


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
