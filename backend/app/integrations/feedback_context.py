from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any


@dataclass
class FeedbackRequestCtx:
    user_agent: str
    request_id: str | None
    langfuse_handler: Any | None


_ctx: ContextVar[FeedbackRequestCtx | None] = ContextVar("feedback_request_ctx", default=None)


def set_feedback_ctx(ctx: FeedbackRequestCtx) -> None:
    _ctx.set(ctx)


def get_feedback_ctx() -> FeedbackRequestCtx | None:
    return _ctx.get()
