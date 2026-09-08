"""«Заявки на вступление»: approving them only for people who are already
subscribed to the chat's required channels.

This is the gate the other way round. The message gate lets a stranger in
and then deletes what they write; here nothing gets in at all — which is
also why it works for channels, where there are no messages to delete.

The applicant is not left to figure it out alone: Telegram hands the bot a
private chat it may write to for five minutes even if that person never
started the bot (`ChatJoinRequest.user_chat_id`), and that is where the
"subscribe to these channels" prompt goes. They do not have to press
anything afterwards either — the moment they subscribe, the channel's
chat_member update brings us back here and the request is approved.
"""

import logging
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import Chat, JoinRequest
from app.screens.join import join_approved_screen, join_prompt_screen
from app.services import chat_service, forcesub_service
from app.services.subscription_checker import check_user
from app.ui import Screen, send

logger = logging.getLogger(__name__)

# Rows for requests an admin handled by hand get no update from Telegram;
# they are cleaned up on approval failure and swept at this age.
STALE_AFTER_DAYS = 30


# --- the pending list -------------------------------------------------------


async def remember(
    session: AsyncSession, chat: Chat, user_tg_id: int, user_chat_id: int | None
) -> None:
    row = await session.get(JoinRequest, {"chat_id": chat.id, "user_tg_id": user_tg_id})
    if row is None:
        session.add(JoinRequest(chat_id=chat.id, user_tg_id=user_tg_id, user_chat_id=user_chat_id))
    else:
        row.user_chat_id = user_chat_id
        row.requested_at = datetime.now(UTC)
    await session.commit()


async def forget(session: AsyncSession, chat_id: int, user_tg_id: int) -> None:
    await session.execute(
        delete(JoinRequest).where(
            JoinRequest.chat_id == chat_id, JoinRequest.user_tg_id == user_tg_id
        )
    )
    await session.commit()


async def pending_for_user(session: AsyncSession, user_tg_id: int) -> list[JoinRequest]:
    return list(
        await session.scalars(select(JoinRequest).where(JoinRequest.user_tg_id == user_tg_id))
    )


async def get_pending(session: AsyncSession, chat: Chat, user_tg_id: int) -> JoinRequest | None:
    return await session.get(JoinRequest, {"chat_id": chat.id, "user_tg_id": user_tg_id})


async def purge_older_than(session: AsyncSession, days: int = STALE_AFTER_DAYS) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = await session.execute(delete(JoinRequest).where(JoinRequest.requested_at < cutoff))
    await session.commit()
    return result.rowcount


# --- deciding ---------------------------------------------------------------


async def approve(bot: Bot, session: AsyncSession, chat: Chat, user_tg_id: int) -> bool:
    """Lets the applicant in and drops the row. False when Telegram refuses
    — usually because an admin already handled the request by hand, so the
    row is dropped either way."""
    try:
        await bot.approve_chat_join_request(chat.telegram_id, user_tg_id)
        approved = True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.info("join request %s/%s not approved: %s", chat.telegram_id, user_tg_id, e)
        approved = False
    await forget(session, chat.id, user_tg_id)
    return approved


async def _tell(bot: Bot, chat_id: int, screen: Screen) -> bool:
    """Writes to the applicant, best effort: they may never have started
    the bot, and the five-minute window may already be over."""
    try:
        await send(bot, chat_id, screen, rich_buttons=True)
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.info("join request: can't write to %s: %s", chat_id, e)
        return False


async def handle_request(
    bot: Bot,
    session: AsyncSession,
    cache: Cache,
    chat: Chat,
    user_tg_id: int,
    user_chat_id: int | None,
    *,
    is_chat_admin: bool = False,
) -> bool:
    """One incoming request. True if it was approved right away."""
    if not chat.join_gate_enabled:
        return False
    channels = await forcesub_service.list_required_channels(session, chat)
    if not channels:
        return False

    whitelist = await forcesub_service.whitelist_ids(session, cache, chat)
    if is_chat_admin or user_tg_id in whitelist:
        return await approve(bot, session, chat, user_tg_id)

    reply_to = user_chat_id or user_tg_id
    result = await check_user(bot, cache, user_tg_id, channels)
    if result.subscribed:
        if not await approve(bot, session, chat, user_tg_id):
            return False
        await _tell(bot, reply_to, join_approved_screen(chat))
        return True

    await remember(session, chat, user_tg_id, user_chat_id)
    screen = await join_prompt_screen(bot, session, chat, result.missing)
    await _tell(bot, reply_to, screen)
    return False


async def recheck(
    bot: Bot, session: AsyncSession, cache: Cache, chat: Chat, user_tg_id: int, *, force: bool
) -> bool:
    """Re-decides one held request. True if the applicant is in now."""
    request = await get_pending(session, chat, user_tg_id)
    if request is None:
        return False
    # Read before approving: the row is gone by then.
    reply_to = request.user_chat_id or user_tg_id

    if not chat.join_gate_enabled:
        # The admin switched the gate off while this one was waiting.
        return await approve(bot, session, chat, user_tg_id)

    channels = await forcesub_service.list_required_channels(session, chat)
    if not channels:
        return await approve(bot, session, chat, user_tg_id)

    result = await check_user(bot, cache, user_tg_id, channels, force=force)
    if not result.subscribed:
        return False
    if not await approve(bot, session, chat, user_tg_id):
        return False
    await _tell(bot, reply_to, join_approved_screen(chat))
    return True


async def recheck_all(
    bot: Bot, session: AsyncSession, cache: Cache, user_tg_id: int, *, force: bool = True
) -> int:
    """Called when someone subscribes to a channel: every request they have
    waiting is decided again. Returns how many were approved.

    `force=False` is for the caller that has just written the fresh
    membership into the cache from the update it is handling; anyone else
    must not trust a value that may be a minute old and say "not
    subscribed" about someone who now is."""
    approved = 0
    for request in await pending_for_user(session, user_tg_id):
        chat = await chat_service.get_chat(session, request.chat_id)
        if chat is None:
            await forget(session, request.chat_id, user_tg_id)
            continue
        if await recheck(bot, session, cache, chat, user_tg_id, force=force):
            approved += 1
    return approved
