from aiogram.types import User as TgUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def upsert_user(
    session: AsyncSession, tg_user: TgUser, *, started: bool | None = None
) -> User:
    """Creates or refreshes the row for a Telegram user. `started=True`
    marks that the user opened a private chat with the bot."""
    user = await get_user_by_telegram_id(session, tg_user.id)
    if user is None:
        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            full_name=tg_user.full_name,
            started_bot=bool(started),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    changed = False
    if user.username != tg_user.username:
        user.username = tg_user.username
        changed = True
    if user.full_name != tg_user.full_name:
        user.full_name = tg_user.full_name
        changed = True
    if started and not user.started_bot:
        user.started_bot = True
        changed = True
    if changed:
        await session.commit()
    return user


async def upsert_user_stub(
    session: AsyncSession, telegram_id: int, username: str | None, full_name: str | None
) -> User:
    """Like upsert_user but from bare fields (e.g. getChatAdministrators)."""
    user = await get_user_by_telegram_id(session, telegram_id)
    if user is None:
        user = User(telegram_id=telegram_id, username=username, full_name=full_name)
        session.add(user)
        await session.flush()
        return user
    if username is not None and user.username != username:
        user.username = username
    if full_name is not None and user.full_name != full_name:
        user.full_name = full_name
    return user


async def set_rich_buttons_enabled(session: AsyncSession, user: User, enabled: bool) -> User:
    user.rich_buttons_enabled = enabled
    await session.commit()
    return user


async def get_users_by_telegram_ids(session: AsyncSession, ids: list[int]) -> dict[int, User]:
    if not ids:
        return {}
    result = await session.scalars(select(User).where(User.telegram_id.in_(ids)))
    return {u.telegram_id: u for u in result}
