from app.commands import parse_slash


def test_parse_slash_with_arg():
    assert parse_slash("/remember foo bar") == ("remember", "foo bar")


def test_parse_slash_no_arg():
    assert parse_slash("/feedback") == ("feedback", "")


def test_parse_slash_multi_word_arg_collapses_whitespace():
    assert parse_slash("/feedback   spaces   inside") == ("feedback", "spaces   inside")


def test_parse_slash_trailing_newline_arg():
    assert parse_slash("/remember\nfoo") == ("remember", "foo")


def test_parse_slash_not_a_command():
    assert parse_slash("hello") is None
    assert parse_slash("") is None
    assert parse_slash("/") is None


def test_parse_slash_invalid_separator():
    # `/remember!stuff` — the char after the name must be space/newline.
    assert parse_slash("/remember!stuff") is None
