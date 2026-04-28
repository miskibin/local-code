from fastapi import APIRouter
from pydantic import BaseModel

from app.auth import CurrentUser, get_or_create_user
from app.config import get_settings
from app.db import async_session
from app.models import User

router = APIRouter()


class LoginRequest(BaseModel):
    email: str


class UserDTO(BaseModel):
    id: str
    email: str
    is_admin: bool = False


def _to_dto(user: User) -> UserDTO:
    admins = {e.lower() for e in get_settings().admin_emails}
    return UserDTO(id=user.id, email=user.email, is_admin=user.email.lower() in admins)


@router.post("/auth/login", response_model=UserDTO)
async def login(req: LoginRequest):
    async with async_session() as s:
        user = await get_or_create_user(s, req.email)
    return _to_dto(user)


@router.get("/auth/me", response_model=UserDTO)
async def me(user: CurrentUser):
    return _to_dto(user)
