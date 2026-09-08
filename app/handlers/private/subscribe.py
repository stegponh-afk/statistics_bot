"""The subscriber's side of «награда за подписку»:
/start sub_<slug> and the «Проверить» button (sub:check:<slug>)."""

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat, User
from app.services import broadcast_delivery, chat_service, reward_service
from app.services.broadcast_service import format_local
from app.services.reward_service import DEEP_LINK_PREFIX
from app.services.subscription_checker import member_status
from app.services.user_service import upsert_user
from app.texts import ru
from app.ui import Btn, Screen, send
from app.ui.buttons import STYLE_PRIMARY, STYLE_SUCCESS
from config import settings

router = Router(name="subscribe")


def _rich(user: User | None) -> bool:
    return user.rich_buttons_enabled if user else True


async def _prompt_screen(bot, session: AsyncSession, channel: Chat) -> Screen:
    link = await chat_service.resolve_invite_link(bot, session, channel)
    rows = []
    if link:
        rows.append([Btn(ru.SUB_BTN_OPEN, link, STYLE_PRIMARY)])
    rows.append([Btn(ru.SUB_BTN_CHECK, f"sub:check:{channel.reward_slug}", STYLE_SUCCESS)])
    return Screen(
        ru.SUB_NEED_SUBSCRIPTION.format(title=channel.title or channel.telegram_id),
        rows=rows,
        has_back_row=False,
    )


async def _deliver(bot, session: AsyncSession, chat_id: int, channel: Chat, user: User) -> None:
    """Hands out the reward once per user; a repeat visit only gets a
    reminder of when it was received."""
    earlier = await reward_service.claim(session, channel, user.telegram_id)
    if earlier is not None:
        when = format_local(earlier.claimed_at, settings.default_timezone)
        await send(bot, chat_id, Screen(ru.SUB_ALREADY.format(when=when)), rich_buttons=_rich(user))
        return
    await send(bot, chat_id, Screen(ru.SUB_OK), rich_buttons=_rich(user))
    content = reward_service.reward_of(channel)
    if content is not None:
        await broadcast_delivery.send_content(bot, chat_id, content, content.file_id)


@router.message(CommandStart(deep_link=True, magic=F.args.startswith(DEEP_LINK_PREFIX)))
async def start_with_reward_link(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    user = await upsert_user(session, message.from_user, started=True)
    slug = reward_service.slug_from_start_arg(command.args)
    channel = await reward_service.channel_by_slug(session, slug or "")
    if channel is None or reward_service.reward_of(channel) is None:
        await send(
            message.bot, message.chat.id, Screen(ru.SUB_LINK_INVALID), rich_buttons=_rich(user)
        )
        return
    status = await member_status(message.bot, channel.telegram_id, message.from_user.id)
    if status is None:
        await send(
            message.bot, message.chat.id, Screen(ru.SUB_UNAVAILABLE), rich_buttons=_rich(user)
        )
        return
    if status[0]:
        await _deliver(message.bot, session, message.chat.id, channel, user)
        return
    await send(
        message.bot,
        message.chat.id,
        await _prompt_screen(message.bot, session, channel),
        rich_buttons=_rich(user),
    )


@router.callback_query(F.data.regexp(r"^sub:check:([A-Za-z0-9]+)$"))
async def cb_sub_check(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    slug = callback.data.rsplit(":", 1)[1]
    channel = await reward_service.channel_by_slug(session, slug)
    if channel is None or reward_service.reward_of(channel) is None:
        await callback.answer(ru.SUB_LINK_INVALID, show_alert=True)
        return
    status = await member_status(callback.bot, channel.telegram_id, callback.from_user.id)
    if status is None:
        await callback.answer(ru.SUB_UNAVAILABLE, show_alert=True)
        return
    if not status[0]:
        await callback.answer(ru.SUB_STILL_MISSING, show_alert=True)
        return
    await callback.answer()
    if user is None:
        user = await upsert_user(session, callback.from_user, started=True)
    await _deliver(callback.bot, session, callback.message.chat.id, channel, user)
