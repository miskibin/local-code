import httpx
import trafilatura
from langchain_core.tools import tool

MAX_CHARS = 8000


@tool
async def web_fetch(url: str) -> str:
    """Fetch a URL and return clean readable text. Use for live web research."""
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "gemma4-harness/0.1"})
            r.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"Error fetching {url}: HTTP {e.response.status_code} {e.response.reason_phrase}"
    except httpx.HTTPError as e:
        return f"Error fetching {url}: {type(e).__name__}: {e}"
    text = trafilatura.extract(r.text) or ""
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n…[truncated]"
    return text
