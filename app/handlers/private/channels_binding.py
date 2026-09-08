"""Which channels a group requires, and the gate on/off switch.

chat:{id}:channels                       the list (✅ / ☐ per channel)
chat:{id}:channels:toggle:{channel_id}   flip one binding
chat:{id}:forcesub                       flip the gate
"""

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import BotStatus, Chat, User
from app.handlers.private.my_chats import load_admin_chat, render_chat_card
from app.services import chat_service, forcesub_service
from app.texts import ru
from app.ui import Btn, Screen, respond

router = Router(name="channels_binding")


async def channels_screen(session: AsyncSession, user: User, chat: Chat) -> Screen:
    channels = await chat_service.list_admin_channels(session, user)
    required = {c.id for c in await forcesub_service.list_required_channels(session, chat)}
    title = chat.title or chat.telegram_id
    if not channels:
        return Screen(
            ru.CHANNELS_EMPTY.format(title=title),
            rows=[[Btn(ru.BTN_REFRESH, "chats:refresh")], [Btn(ru.BTN_BACK, f"chat:{chat.id}")]],
        )
    rows = [
        [
            Btn(
                (ru.CHANNEL_ROW_ON if c.id in required else ru.CHANNEL_ROW_OFF).format(
                    title=c.title or c.telegram_id
                ),
                f"chat:{chat.id}:channels:toggle:{c.id}",
            )
        ]
        for c in channels
    ]
    rows.append([Btn(ru.BTN_BACK, f"chat:{chat.id}")])
    return Screen(ru.CHANNELS_TITLE.format(title=title), rows=rows)


@router.callback_query(F.data.regexp(r"^chat:(\d+):channels$"))
async def cb_channels(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    if user is None:
        await callback.answer()
        return
    chat = await load_admin_chat(session, user, int(callback.data.split(":")[1]))
    if chat is None:
        await callback.answer(ru.CHAT_NOT_FOUND, show_alert=True)
        return
    await respond(
        callback, await channels_screen(session, user, chat), rich_buttons=user.rich_buttons_enabled
    )


@router.callback_query(F.data.regexp(r"^chat:(\d+):channels:toggle:(\d+)$"))
async def cb_channel_toggle(
    callback: CallbackQuery, session: AsyncSession, user: User | None, cache: Cache
) -> None:
    if user is None:
        await callback.answer()
        return
    parts = callback.data.split(":")
    chat = await load_admin_chat(session, user, int(parts[1]))
    channel = await load_admin_chat(session, user, int(parts[4]))
    if chat is None or channel is None or not channel.is_channel:
        await callback.answer(ru.CHAT_NOT_FOUND, show_alert=True)
        return

    already = channel.id in {
        c.id for c in await forcesub_service.list_required_channels(session, chat)
    }
    if not already:
        # Binding a channel the bot can't actually query would silently
        # fail-open later; verify the admin status right now.
        try:
            me = await callback.bot.get_chat_member(channel.telegram_id, callback.bot.id)
            is_admin = me.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)
        except (TelegramBadRequest, TelegramForbiddenError):
            is_admin = False
        if not is_admin:
            channel.bot_status = BotStatus.LEFT
            await session.commit()
            await callback.answer(
                ru.CHANNEL_BOT_NOT_ADMIN.format(title=channel.title or channel.telegram_id),
                show_alert=True,
            )
            await respond(
                callback,
                await channels_screen(session, user, chat),
                rich_buttons=user.rich_buttons_enabled,
            )
            return

    now_required = await forcesub_service.toggle_required_channel(session, cache, chat, channel)
    if not now_required and not await forcesub_service.list_required_channels(session, chat):
        await forcesub_service.set_forcesub_enabled(session, chat, False)
    await callback.answer(ru.CHANNEL_ADDED if now_required else ru.CHANNEL_REMOVED)
    await respond(
        callback, await channels_screen(session, user, chat), rich_buttons=user.rich_buttons_enabled
    )


@router.callback_query(F.data.regexp(r"^chat:(\d+):forcesub$"))
async def cb_forcesub_toggle(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    chat = await load_admin_chat(session, user, int(callback.data.split(":")[1]))
    if chat is None or chat.is_channel:
        await callback.answer(ru.CHAT_NOT_FOUND, show_alert=True)
        return

    if chat.forcesub_enabled:
        await forcesub_service.set_forcesub_enabled(session, chat, False)
        await callback.answer(ru.FORCESUB_DISABLED)
    else:
        if not await forcesub_service.list_required_channels(session, chat):
            await callback.answer(ru.FORCESUB_NEED_CHANNELS, show_alert=True)
            return
        if not chat.bot_can_delete:
            await callback.answer(ru.FORCESUB_NEED_DELETE_RIGHT, show_alert=True)
            return
        await forcesub_service.set_forcesub_enabled(session, chat, True)
        await callback.answer(ru.FORCESUB_ENABLED)

    screen = await render_chat_card(callback.bot, session, chat)
    await respond(callback, screen, rich_buttons=user.rich_buttons_enabled)


@router.callback_query(F.data.regexp(r"^chat:(\d+):comments_gate$"))
async def cb_comments_gate_toggle(
    callback: CallbackQuery, session: AsyncSession, user: User | None, cache: Cache
) -> None:
    """On a channel's card: require a channel subscription to comment,
    i.e. bind the channel in its discussion group and switch that group's
    gate."""
    if user is None:
        await callback.answer()
        return
    channel = await load_admin_chat(session, user, int(callback.data.split(":")[1]))
    if channel is None or not channel.is_channel:
        await callback.answer(ru.CHAT_NOT_FOUND, show_alert=True)
        return
    group = await chat_service.resolve_linked_group(callback.bot, session, channel, refresh=True)
    if group is None:
        await callback.answer(ru.COMMENTS_GATE_NO_GROUP, show_alert=True)
        return

    enabled = await forcesub_service.comments_gate_enabled(session, channel, group)
    if enabled:
        await forcesub_service.set_comments_gate(session, cache, channel, group, False)
        await callback.answer(ru.COMMENTS_GATE_DISABLED)
    else:
        await chat_service.refresh_bot_membership(callback.bot, session, group)
        if not group.bot_can_delete:
            await callback.answer(
                ru.COMMENTS_GATE_NEED_DELETE_RIGHT.format(title=group.title or group.telegram_id),
                show_alert=True,
            )
            return
        await forcesub_service.set_comments_gate(session, cache, channel, group, True)
        await callback.answer(ru.COMMENTS_GATE_ENABLED)

    screen = await render_chat_card(callback.bot, session, channel)
    await respond(callback, screen, rich_buttons=user.rich_buttons_enabled)
