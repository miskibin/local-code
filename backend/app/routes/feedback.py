from fastapi import APIRouter, HTTPException
from langfuse import get_client
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter()


class FeedbackBody(BaseModel):
    traceId: str
    value: int
    comment: str | None = None


@router.post("/feedback")
async def post_feedback(body: FeedbackBody):
    if not get_settings().langfuse_secret_key:
        raise HTTPException(503, "langfuse not configured")
    get_client().create_score(
        trace_id=body.traceId,
        name="user-feedback",
        value=body.value,
        data_type="NUMERIC",
        comment=body.comment,
    )
    return {"ok": True}
