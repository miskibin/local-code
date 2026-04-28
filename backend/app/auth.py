from typing import Annotated
from uuid import uuid4

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import get_settings
from app.db import async_session
from app.models import User

_MIN_EMAIL_LEN = 3


def _normalize_email(value: str) -> str:
    email = value.strip().lower()
    if "@" not in email or len(email) < _MIN_EMAIL_LEN:
        raise HTTPException(400, "invalid email")
    return email


async def get_or_create_user(s: AsyncSession, email: str) -> User:
    email = _normalize_email(email)
    existing = (await s.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing is not None:
        return existing
    user = User(id=f"usr_{uuid4().hex[:12]}", email=email)
    s.add(user)
    await s.commit()
    await s.refresh(user)
    return user


async def current_user(
    x_user_email: Annotated[str | None, Header()] = None,
) -> User:
    if not x_user_email:
        raise HTTPException(401, "missing X-User-Email header")
    async with async_session() as s:
        return await get_or_create_user(s, x_user_email)


CurrentUser = Annotated[User, Depends(current_user)]


async def current_admin(user: CurrentUser) -> User:
    admins = {e.lower() for e in get_settings().admin_emails}
    if user.email.lower() not in admins:
        raise HTTPException(403, "admin only")
    return user


CurrentAdmin = Annotated[User, Depends(current_admin)]
