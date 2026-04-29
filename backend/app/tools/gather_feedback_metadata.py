from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langfuse import get_client
from loguru import logger

from app.config import get_settings
from app.integrations.feedback_context import get_feedback_ctx


@tool
def gather_feedback_metadata(config: RunnableConfig) -> dict[str, Any]:
    """Collect technical metadata to attach to a feedback issue.

    Returns a dict with reporter, session id, app version, git sha, langfuse
    trace url, browser user-agent. Call this once before drafting the issue.
    """
    configurable = (config or {}).get("configurable") or {}
    ctx = get_feedback_ctx()
    handler = ctx.langfuse_handler if ctx else None
    trace_id = getattr(handler, "last_trace_id", None) if handler else None
    trace_url: str | None = None
    if trace_id and get_settings().langfuse_secret_key:
        try:
            trace_url = get_client().get_trace_url(trace_id=trace_id)
        except Exception as e:  # noqa: BLE001 -- best-effort
            logger.warning(f"langfuse trace url lookup failed: {e!r}")
    return {
        "reporter_email": configurable.get("reporter_email", ""),
        "session_id": configurable.get("thread_id", ""),
        "app_version": configurable.get("app_version", ""),
        "git_sha": configurable.get("git_sha", ""),
        "user_agent": ctx.user_agent if ctx else "",
        "request_id": ctx.request_id if ctx else None,
        "langfuse_trace_id": trace_id,
        "langfuse_trace_url": trace_url,
    }
