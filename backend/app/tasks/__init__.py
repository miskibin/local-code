from __future__ import annotations

from typing import Any


def coerce_lc_content(content: Any, *, fallback: str = "") -> str:
    """Flatten LangChain message content (str | list[block]) to plain text.

    `fallback` is returned when content is empty/unknown shape (generator wants
    "" so missing turns are silent; runner passes nothing so the final
    `str(content)` branch fires for non-text dicts).
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                out.append(str(c.get("text", "")))
        return "".join(out)
    if not content:
        return fallback
    return str(content)
