import ipaddress
import socket
from urllib.parse import urlparse, urlsplit, urlunsplit

import httpx
import trafilatura
from langchain_core.tools import ToolException, tool
from loguru import logger

MAX_CHARS = 8000
MAX_BODY_BYTES = 2 * 1024 * 1024
ALLOWED_SCHEMES = ("http", "https")


def _strip_userinfo(url: str) -> str:
    parts = urlsplit(url)
    if "@" in parts.netloc:
        host = parts.netloc.split("@", 1)[1]
        parts = parts._replace(netloc=host)
    return urlunsplit(parts)


def _validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ToolException(f"scheme {parsed.scheme!r} not allowed; use http or https")
    host = parsed.hostname
    if not host:
        raise ToolException("url has no host")
    try:
        infos = socket.getaddrinfo(host, parsed.port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise ToolException(f"dns failure for {host!r}: {e}") from e
    for _family, _, _, _, sockaddr in infos:
        ip_str = sockaddr[0]
        ip = ipaddress.ip_address(ip_str)
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ToolException(f"refusing to fetch internal address {ip_str} for host {host!r}")
    return _strip_userinfo(url)


@tool
async def web_fetch(url: str) -> str:
    """Fetch a URL and return clean readable text. Use for live web research."""
    safe_url = _validate_url(url)
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            r = await client.get(safe_url, headers={"User-Agent": "gemma4-harness/0.1"})
            while r.is_redirect:
                loc = r.headers.get("location")
                if not loc:
                    raise ToolException(f"redirect without Location from {safe_url!r}")
                next_url = _validate_url(str(httpx.URL(safe_url).join(loc)))
                r = await client.get(next_url, headers={"User-Agent": "gemma4-harness/0.1"})
                safe_url = next_url
            r.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.warning(f"web_fetch fail url={safe_url}: HTTP {e.response.status_code}")
        raise ToolException(
            f"Error fetching {safe_url}: HTTP {e.response.status_code} {e.response.reason_phrase}"
        ) from e
    except httpx.HTTPError as e:
        logger.warning(f"web_fetch fail url={safe_url}: {type(e).__name__}: {e}")
        raise ToolException(f"Error fetching {safe_url}: {type(e).__name__}: {e}") from e
    body = r.content if hasattr(r, "content") else b""
    if isinstance(body, bytes) and len(body) > MAX_BODY_BYTES:
        raise ToolException(f"response body exceeded {MAX_BODY_BYTES} bytes for {safe_url!r}")
    raw = r.text
    logger.debug(f"web_fetch ok url={safe_url} bytes={len(raw)}")
    text = trafilatura.extract(raw) or ""
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n…[truncated]"
    return text


web_fetch.handle_tool_error = True
