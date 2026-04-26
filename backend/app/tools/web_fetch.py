import httpx
import trafilatura
from langchain_core.tools import ToolException, tool
from loguru import logger

MAX_CHARS = 8000


@tool
async def web_fetch(url: str) -> str:
    """Fetch a URL and return clean readable text. Use for live web research."""
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "gemma4-harness/0.1"})
            r.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.warning(f"web_fetch fail url={url}: HTTP {e.response.status_code}")
        raise ToolException(
            f"Error fetching {url}: HTTP {e.response.status_code} {e.response.reason_phrase}"
        ) from e
    except httpx.HTTPError as e:
        logger.warning(f"web_fetch fail url={url}: {type(e).__name__}: {e}")
        raise ToolException(f"Error fetching {url}: {type(e).__name__}: {e}") from e
    logger.debug(f"web_fetch ok url={url} status={r.status_code} bytes={len(r.text)}")
    text = trafilatura.extract(r.text) or ""
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n…[truncated]"
    return text


web_fetch.handle_tool_error = True
