import re
from datetime import UTC, datetime
from typing import Any

ARTIFACT_ID_RE = re.compile(r"art_[0-9a-f]{8,}")
ARTIFACT_DOT_PREFIX_RE = re.compile(r"^\s*(art_[A-Za-z0-9]+)\s*·")


def now_utc() -> datetime:
    return datetime.now(UTC)


def extract_text(content: Any) -> str:
    """Flatten LangChain message content (str | list of parts) to a plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out: list[str] = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                out.append(str(c.get("text", "")))
            elif isinstance(c, str):
                out.append(c)
        return "".join(out)
    return ""


def coerce_output(content: Any) -> object:
    """Normalize message content into a string or pass-through scalar."""
    if isinstance(content, (str, int, float, bool)) or content is None:
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(str(c.get("text", "")))
            else:
                parts.append(str(c))
        return "".join(parts)
    return str(content)
