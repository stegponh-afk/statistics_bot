"""One `Screen` = the text + buttons of a full-message view. The functions
below render it as a rich message (new style) or classic keyboard (old
style) and know how to deliver it in every context this bot works in:

- send / edit               — private chats (and public group posts)
- send_ephemeral            — a message in a group only one user can see
- edit_ephemeral            — editing such a message in place
- respond                   — answering a button press wherever it came from
- reply_to_command          — answering /command: ephemeral in groups

Everything falls back to plain HTML text + inline keyboard when Telegram
rejects the rich form, so a screen is never silently lost.

InputRichMessage is a frozen pydantic model — never mutate `.blocks`,
always construct a new one (the reference bot learned this the hard way).
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import (
    CallbackQuery,
    EphemeralMessageParameters,
    InlineKeyboardMarkup,
    InputRichBlockUnion,
    InputRichMessage,
    Message,
    ReplyParameters,
)

from app.ui.blocks import rich_blocks_from_legacy_text
from app.ui.buttons import ButtonRow, apply_button_style, keyboard_from_rows

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Screen:
    text: str
    rows: Sequence[ButtonRow] = field(default_factory=list)
    # Extra rich blocks (tables, lists) inserted after the text blocks.
    extra_blocks: Sequence[InputRichBlockUnion] = field(default_factory=list)
    has_back_row: bool = True

    def as_rich(
        self, *, rich_buttons: bool
    ) -> tuple[InputRichMessage, InlineKeyboardMarkup | None]:
        blocks = [*rich_blocks_from_legacy_text(self.text), *self.extra_blocks]
        blocks, keyboard = apply_button_style(
            blocks,
            list(self.rows),
            rich_buttons_enabled=rich_buttons,
            has_back_row=self.has_back_row,
        )
        return InputRichMessage(blocks=blocks), keyboard

    def as_text(self) -> tuple[str, InlineKeyboardMarkup | None]:
        return self.text, (keyboard_from_rows(list(self.rows)) if self.rows else None)


# --- sending ------------------------------------------------------------


async def send(
    bot: Bot, chat_id: int, screen: Screen, *, rich_buttons: bool, thread_id: int | None = None
) -> Message:
    rich, keyboard = screen.as_rich(rich_buttons=rich_buttons)
    try:
        return await bot.send_rich_message(
            chat_id, rich_message=rich, reply_markup=keyboard, message_thread_id=thread_id
        )
    except TelegramBadRequest as e:
        logger.warning("rich send rejected, falling back to text: %s", e)
        text, keyboard = screen.as_text()
        return await bot.send_message(
            chat_id, text, reply_markup=keyboard, message_thread_id=thread_id
        )


async def send_ephemeral(
    bot: Bot,
    chat_id: int,
    receiver_user_id: int,
    screen: Screen,
    *,
    rich_buttons: bool,
    callback_query_id: str | None = None,
    replace_callback_query_message: bool | None = None,
    reply_to: Message | None = None,
    thread_id: int | None = None,
) -> Message | None:
    """A message in a group that only `receiver_user_id` can see. Returns
    None (never raises) when Telegram won't deliver it — e.g. the user is
    offline — because there is nothing sensible to do about that."""
    params = EphemeralMessageParameters(
        receiver_user_id=receiver_user_id,
        callback_query_id=callback_query_id,
        replace_callback_query_message=replace_callback_query_message,
    )
    reply_params = None
    if reply_to is not None and reply_to.ephemeral_message_id:
        # A reply to an ephemeral message must itself be ephemeral and go
        # out within 15 s of the original.
        reply_params = ReplyParameters(
            message_id=reply_to.message_id, ephemeral_message_id=reply_to.ephemeral_message_id
        )

    rich, keyboard = screen.as_rich(rich_buttons=rich_buttons)
    try:
        return await bot.send_rich_message(
            chat_id,
            rich_message=rich,
            reply_markup=keyboard,
            ephemeral_message_parameters=params,
            reply_parameters=reply_params,
            message_thread_id=thread_id,
        )
    except TelegramBadRequest as e:
        logger.warning("rich ephemeral send rejected, falling back to text: %s", e)
    except TelegramForbiddenError as e:
        logger.info("ephemeral send forbidden: %s", e)
        return None

    text, keyboard = screen.as_text()
    try:
        return await bot.send_message(
            chat_id,
            text,
            reply_markup=keyboard,
            ephemeral_message_parameters=params,
            reply_parameters=reply_params,
            message_thread_id=thread_id,
        )
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.warning("ephemeral text send failed: %s", e)
        return None


# --- editing ------------------------------------------------------------


async def edit(message: Message, screen: Screen, *, rich_buttons: bool) -> None:
    """Replaces the screen a (private-chat) message is showing. A rich
    message is its own content type, so editing a plain-text message into
    one can be rejected — then it's delete + resend."""
    rich, keyboard = screen.as_rich(rich_buttons=rich_buttons)
    try:
        await message.edit_text(rich_message=rich, reply_markup=keyboard)
        return
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        logger.debug("rich edit rejected (%s), resending", e)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    await send(message.bot, message.chat.id, screen, rich_buttons=rich_buttons)


async def edit_ephemeral(
    bot: Bot,
    chat_id: int,
    receiver_user_id: int,
    ephemeral_message_id: int,
    screen: Screen,
    *,
    rich_buttons: bool,
) -> bool:
    rich, keyboard = screen.as_rich(rich_buttons=rich_buttons)
    try:
        await bot.edit_ephemeral_message_text(
            chat_id=chat_id,
            receiver_user_id=receiver_user_id,
            ephemeral_message_id=ephemeral_message_id,
            rich_message=rich,
            reply_markup=keyboard,
        )
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return True
        logger.warning("rich ephemeral edit rejected, trying text: %s", e)
    text, keyboard = screen.as_text()
    try:
        await bot.edit_ephemeral_message_text(
            chat_id=chat_id,
            receiver_user_id=receiver_user_id,
            ephemeral_message_id=ephemeral_message_id,
            text=text,
            reply_markup=keyboard,
        )
        return True
    except TelegramBadRequest as e:
        logger.warning("ephemeral edit failed: %s", e)
        return False


# --- answering a button press --------------------------------------------


async def respond(callback: CallbackQuery, screen: Screen, *, rich_buttons: bool) -> None:
    """Shows `screen` to whoever pressed the button, wherever the button was:

    - inside an ephemeral message  -> edit that ephemeral message in place
    - inside a public group post   -> a new ephemeral message shown in place
                                      of the post, for this user only
    - in a private chat            -> edit the message
    """
    message = callback.message
    bot = callback.bot

    if isinstance(message, Message) and message.ephemeral_message_id:
        ok = await edit_ephemeral(
            bot,
            message.chat.id,
            callback.from_user.id,
            message.ephemeral_message_id,
            screen,
            rich_buttons=rich_buttons,
        )
        if not ok:
            await send_ephemeral(
                bot, message.chat.id, callback.from_user.id, screen, rich_buttons=rich_buttons
            )
        await callback.answer()
        return

    if message is None:
        await callback.answer()
        return

    if message.chat.type == ChatType.PRIVATE:
        if isinstance(message, Message):
            await edit(message, screen, rich_buttons=rich_buttons)
        else:
            await send(bot, message.chat.id, screen, rich_buttons=rich_buttons)
        await callback.answer()
        return

    sent = await send_ephemeral(
        bot,
        message.chat.id,
        callback.from_user.id,
        screen,
        rich_buttons=rich_buttons,
        callback_query_id=callback.id,
        replace_callback_query_message=True,
    )
    if sent is None:
        await callback.answer()


async def reply_to_command(
    message: Message, screen: Screen, *, rich_buttons: bool, delete_public: bool = False
) -> Message | None:
    """Answers a /command: a normal message in private, ephemeral in groups.
    With delete_public, a command the user typed publicly (as opposed to
    picking it from the bot menu, which is invisible anyway) is removed
    afterwards so the chat doesn't fill up with /stats lines."""
    if message.chat.type == ChatType.PRIVATE:
        return await send(message.bot, message.chat.id, screen, rich_buttons=rich_buttons)

    if message.from_user is None:
        return None
    sent = await send_ephemeral(
        message.bot,
        message.chat.id,
        message.from_user.id,
        screen,
        rich_buttons=rich_buttons,
        reply_to=message,
        thread_id=message.message_thread_id if message.is_topic_message else None,
    )
    if delete_public and not message.ephemeral_message_id:
        try:
            await message.delete()
        except (TelegramBadRequest, TelegramForbiddenError):
            pass
    return sent
