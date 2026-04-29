_NAME_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")


def parse_slash(text: str) -> tuple[str, str] | None:
    """Parse `/name [arg...]` from a free-form chat message.

    Returns `(name, arg)` (arg may be empty) or `None` when text doesn't start
    with a `/` followed by a valid name character. The leading `/` and any
    trailing newline-prefixed continuation are honoured; only the first line
    is parsed for the command name and its argument is the rest of the input
    (including subsequent lines).
    """
    if not text or not text.startswith("/"):
        return None
    body = text[1:]
    if not body or body[0] not in _NAME_CHARS:
        return None
    i = 0
    while i < len(body) and body[i] in _NAME_CHARS:
        i += 1
    name = body[:i]
    rest = body[i:]
    if rest.startswith((" ", "\n")):
        rest = rest[1:]
    elif rest:
        return None
    return name, rest.strip()
