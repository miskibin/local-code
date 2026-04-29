from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class CommandDTO(BaseModel):
    name: str
    description: str
    arg_hint: str


@router.get("/commands", response_model=list[CommandDTO])
async def list_commands(request: Request) -> list[CommandDTO]:
    registry = getattr(request.app.state, "commands", {}) or {}
    return [
        CommandDTO(name=c.name, description=c.description, arg_hint=c.arg_hint)
        for c in sorted(registry.values(), key=lambda c: c.name)
    ]
