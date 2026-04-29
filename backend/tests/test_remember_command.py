from types import SimpleNamespace

import pytest

from app.commands.base import CommandContext, StaticResult
from app.commands.remember import command as remember_cmd
from app.db import async_session
from app.models import User, UserInstructions
from app.utils import now_utc
from tests.conftest import reset_task_tables


@pytest.mark.asyncio
async def test_remember_appends_to_user_instructions():
    await reset_task_tables(UserInstructions, User)
    async with async_session() as s:
        s.add(User(id="usr_remember", email="r@example.com", created_at=now_utc()))
        await s.commit()

    user = SimpleNamespace(id="usr_remember", email="r@example.com")
    ctx = CommandContext(request=None, user=user, session_id="sess_x")  # type: ignore[arg-type]

    result = await remember_cmd.handle(arg="always reply in Polish", ctx=ctx)
    assert isinstance(result, StaticResult)
    assert result.text == "Remembered: always reply in Polish"

    async with async_session() as s:
        ui = await s.get(UserInstructions, "usr_remember")
    assert ui is not None
    assert ui.content == "- always reply in Polish"

    await remember_cmd.handle(arg="prefer concise answers", ctx=ctx)
    async with async_session() as s:
        ui = await s.get(UserInstructions, "usr_remember")
    assert ui is not None
    assert ui.content == "- always reply in Polish\n- prefer concise answers"


@pytest.mark.asyncio
async def test_remember_empty_arg_is_help():
    await reset_task_tables(UserInstructions, User)
    async with async_session() as s:
        s.add(User(id="usr_empty", email="e@example.com", created_at=now_utc()))
        await s.commit()

    user = SimpleNamespace(id="usr_empty", email="e@example.com")
    ctx = CommandContext(request=None, user=user, session_id="sess_x")  # type: ignore[arg-type]

    result = await remember_cmd.handle(arg="   ", ctx=ctx)
    assert isinstance(result, StaticResult)
    assert "needs some text" in result.text.lower()

    async with async_session() as s:
        ui = await s.get(UserInstructions, "usr_empty")
    assert ui is None


@pytest.mark.asyncio
async def test_remember_enforces_max_lines():
    from app.commands.remember import MAX_LINES

    await reset_task_tables(UserInstructions, User)
    async with async_session() as s:
        s.add(User(id="usr_cap", email="c@example.com", created_at=now_utc()))
        s.add(
            UserInstructions(
                user_id="usr_cap",
                content="\n".join(f"- note {i}" for i in range(MAX_LINES)),
                updated_at=now_utc(),
            )
        )
        await s.commit()

    user = SimpleNamespace(id="usr_cap", email="c@example.com")
    ctx = CommandContext(request=None, user=user, session_id="sess_x")  # type: ignore[arg-type]

    result = await remember_cmd.handle(arg="one more note", ctx=ctx)
    assert isinstance(result, StaticResult)
    assert "limit" in result.text.lower()

    async with async_session() as s:
        ui = await s.get(UserInstructions, "usr_cap")
    assert ui is not None
    assert "one more note" not in ui.content
