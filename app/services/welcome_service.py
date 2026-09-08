"""«Приветствие»: what happens the moment somebody joins a group.

Two things, either of which the admin can switch on:

- the greeting itself — a stored message (text/media/buttons) delivered to
  the newcomer. By default it is *ephemeral*: only they see it, so a busy
  chat is not buried under "Welcome!" lines.
- the captcha — the newcomer is muted until they press «Я не бот», which
  costs a spam account the one thing it does not have: a human tap.

The captcha must never be able to strand a real person: if the challenge
cannot be delivered (ephemeral refused *and* the public fallback refused),
the mute is lifted immediately.
"""

import html
import logging
from dataclasses import replace

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ChatPermissions, EphemeralMessageParameters
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import Chat
from app.services.broadcast_delivery import send_content
from app.services.broadcast_service import Content
from app.texts import ru
from app.ui import Btn, Screen, send, send_ephemeral
from app.ui.buttons import STYLE_SUCCESS

logger = logging.getLogger(__name__)

# How long a pending captcha is remembered. Only a user with a pending
# challenge can be un-muted by the button, so pressing someone else's (or
# a stale) button does nothing.
CAPTCHA_TTL = 24 * 3600

_MUTED = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
)
# Used only when getChat will not tell us the chat's own defaults.
_UNMUTED = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
)


def captcha_key(chat_tg_id: int, user_tg_id: int) -> str:
    return f"cap:{chat_tg_id}:{user_tg_id}"


def _title(chat: Chat) -> str:
    return str(chat.title or chat.telegram_id)


# --- the stored greeting ----------------------------------------------------


def welcome_of(chat: Chat) -> Content | None:
    return Content.from_json(chat.welcome_content) if chat.welcome_content else None


async def set_welcome(session: AsyncSession, chat: Chat, content: Content) -> None:
    chat.welcome_content = content.to_json()
    chat.welcome_enabled = True
    await session.commit()


async def clear_welcome(session: AsyncSession, chat: Chat) -> None:
    chat.welcome_content = None
    chat.welcome_enabled = False
    await session.commit()


def render(content: Content, *, name: str, title: str) -> Content:
    """Substitutes {name} and {title}.

    Skipped when the admin formatted the message in Telegram: that
    formatting arrives as entities with absolute offsets, which any
    substitution would shift onto the wrong characters.
    """
    text = content.text
    if not text or content.entities:
        return content
    if content.parse_mode == "HTML":
        name, title = html.escape(name), html.escape(title)
    return replace(content, text=text.replace("{name}", name).replace("{title}", title))


# --- muting -----------------------------------------------------------------


async def mute(bot: Bot, chat: Chat, user_tg_id: int) -> bool:
    try:
        await bot.restrict_chat_member(chat.telegram_id, user_tg_id, permissions=_MUTED)
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.warning("captcha: can't mute %s in %s: %s", user_tg_id, chat.telegram_id, e)
        return False


async def unmute(bot: Bot, chat: Chat, user_tg_id: int) -> bool:
    """Gives the member back exactly the chat's default permissions."""
    permissions = _UNMUTED
    try:
        info = await bot.get_chat(chat.telegram_id)
        permissions = getattr(info, "permissions", None) or _UNMUTED
    except (TelegramBadRequest, TelegramForbiddenError):
        pass
    try:
        await bot.restrict_chat_member(chat.telegram_id, user_tg_id, permissions=permissions)
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.warning("captcha: can't unmute %s in %s: %s", user_tg_id, chat.telegram_id, e)
        return False


# --- screens ----------------------------------------------------------------


def captcha_screen(chat: Chat, name: str) -> Screen:
    text = ru.CAPTCHA_PROMPT.format(name=html.escape(name), title=html.escape(_title(chat)))
    return Screen(
        text,
        rows=[[Btn(ru.BTN_CAPTCHA_OK, f"wc:ok:{chat.telegram_id}", STYLE_SUCCESS)]],
        has_back_row=False,
    )


def text_screen(chat: Chat, name: str) -> Screen | None:
    """The greeting as a plain screen — only for a text-only message with
    no entity formatting and no buttons, which is what a Screen carries."""
    content = welcome_of(chat)
    if content is None or content.is_media or content.entities or content.buttons:
        return None
    rendered = render(content, name=name, title=_title(chat))
    return Screen(rendered.text or "", has_back_row=False)


# --- delivery ---------------------------------------------------------------


async def deliver_welcome(
    bot: Bot, chat: Chat, user_tg_id: int, name: str, *, thread_id: int | None = None
) -> bool:
    """Sends the stored greeting. Ephemeral first when the admin chose it,
    falling back to a normal message rather than losing the greeting."""
    content = welcome_of(chat)
    if content is None:
        return False
    content = render(content, name=name, title=_title(chat))

    if chat.welcome_ephemeral:
        params = EphemeralMessageParameters(receiver_user_id=user_tg_id)
        try:
            await send_content(
                bot,
                chat.telegram_id,
                content,
                content.file_id,
                ephemeral=params,
                thread_id=thread_id,
            )
            return True
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            logger.info(
                "welcome: ephemeral refused in %s (%s), sending openly", chat.telegram_id, e
            )

    try:
        await send_content(bot, chat.telegram_id, content, content.file_id, thread_id=thread_id)
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.warning("welcome: not delivered in %s: %s", chat.telegram_id, e)
        return False


async def _deliver_captcha(bot: Bot, chat: Chat, user_tg_id: int, name: str) -> bool:
    screen = captcha_screen(chat, name)
    if await send_ephemeral(bot, chat.telegram_id, user_tg_id, screen, rich_buttons=True):
        return True
    try:
        await send(bot, chat.telegram_id, screen, rich_buttons=True)
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.warning("captcha: challenge not delivered in %s: %s", chat.telegram_id, e)
        return False


async def on_join(bot: Bot, cache: Cache, chat: Chat, user_tg_id: int, name: str) -> None:
    """A human joined a group the bot administers."""
    if not chat.is_active:
        return

    if chat.captcha_enabled and chat.bot_can_restrict and await mute(bot, chat, user_tg_id):
        await cache.set(captcha_key(chat.telegram_id, user_tg_id), "1", CAPTCHA_TTL)
        if await _deliver_captcha(bot, chat, user_tg_id, name):
            return  # the greeting follows once they pass
        # Nobody may be left muted by a challenge they never saw.
        await cache.delete(captcha_key(chat.telegram_id, user_tg_id))
        await unmute(bot, chat, user_tg_id)

    if chat.welcome_enabled:
        await deliver_welcome(bot, chat, user_tg_id, name)


async def pass_captcha(bot: Bot, cache: Cache, chat: Chat, user_tg_id: int) -> bool:
    """True if this user really had a challenge pending and is now free."""
    key = captcha_key(chat.telegram_id, user_tg_id)
    if await cache.get(key) is None:
        return False
    await cache.delete(key)
    await unmute(bot, chat, user_tg_id)
    return True
