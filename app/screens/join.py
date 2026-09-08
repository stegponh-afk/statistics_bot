"""What an applicant sees in their private chat while their join request
is held: which channels to subscribe to, and the confirmation."""

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat
from app.services import chat_service
from app.texts import ru
from app.ui import Btn, Screen
from app.ui.buttons import STYLE_PRIMARY, STYLE_SUCCESS


async def join_prompt_screen(
    bot: Bot, session: AsyncSession, chat: Chat, missing: list[Chat]
) -> Screen:
    lines: list[str] = []
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
    rows.append([Btn(ru.JOIN_BTN_CHECK, f"jr:check:{chat.telegram_id}", STYLE_SUCCESS)])
    text = ru.JOIN_PROMPT.format(title=chat.title or chat.telegram_id, channels="\n".join(lines))
    return Screen(text, rows=rows, has_back_row=False)


def join_approved_screen(chat: Chat) -> Screen:
    return Screen(ru.JOIN_APPROVED.format(title=chat.title or chat.telegram_id), has_back_row=False)
