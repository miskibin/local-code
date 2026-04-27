from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_web_fetch_returns_extracted_text():
    from app.tools.web_fetch import web_fetch

    html = "<html><body><article>Hello there world.</article></body></html>"
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    mock_resp.content = html.encode("utf-8")
    mock_resp.is_redirect = False
    mock_resp.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        result = await web_fetch.ainvoke({"url": "https://example.com"})
    assert "Hello there world" in result


@pytest.mark.asyncio
async def test_web_fetch_truncates_long_output():
    from app.tools.web_fetch import MAX_CHARS, web_fetch

    html = "<html><body><article>" + "x" * (MAX_CHARS * 2) + "</article></body></html>"
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.text = html
    mock_resp.content = html.encode("utf-8")
    mock_resp.is_redirect = False
    mock_resp.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        result = await web_fetch.ainvoke({"url": "https://example.com"})
    assert len(result) <= MAX_CHARS + 32  # truncation marker
