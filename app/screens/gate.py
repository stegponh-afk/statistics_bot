"""The ephemeral screens the force-sub gate shows to an unsubscribed user."""

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat
from app.services import chat_service
from app.texts import ru
from app.ui import Btn, Screen
from app.ui.buttons import STYLE_PRIMARY, STYLE_SUCCESS


async def gate_prompt_screen(
    bot: Bot, session: AsyncSession, chat: Chat, missing: list[Chat]
) -> Screen:
    lines = []
    rows: list[list[Btn]] = []
    for channel in missing:
        title = channel.title or str(channel.telegram_id)
        link = await chat_service.resolve_invite_link(bot, session, channel)
        line = ru.GATE_CHANNEL_LINE.format(title=title)
        if link:
            rows.append([Btn(ru.GATE_BTN_SUBSCRIBE.format(title=title), link, STYLE_PRIMARY)])
        else:
            line += ru.GATE_CHANNEL_NO_LINK
        lines.append(line)
    rows.append([Btn(ru.GATE_BTN_CHECK, f"gate:check:{chat.telegram_id}", STYLE_SUCCESS)])
    text = ru.GATE_PROMPT.format(title=chat.title or chat.telegram_id, channels="\n".join(lines))
    return Screen(text, rows=rows, has_back_row=False)


def gate_ok_screen() -> Screen:
    return Screen(ru.GATE_OK)
