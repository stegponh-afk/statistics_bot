"""Old vs new button style.

A screen builds its buttons once as `rows` — every row a list of Btn
(text, target, optional style), the back row last — and apply_button_style
picks the rendering from the user's rich_buttons_enabled preference:

- old: every row as the usual inline keyboard below the message.
- new: every row embedded as InputRichBlockButtons inside the message (a
  Divider before them), with the back row alone below a second Divider, and
  no reply_markup at all.

`target` is a callback_data string, or an http(s) URL for a link button —
this bot's callback_data never looks like a URL, so the check is unambiguous.
"""

from typing import NamedTuple

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputRichBlockButtons,
    InputRichBlockDivider,
    InputRichBlockUnion,
    RichMessageButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


class Btn(NamedTuple):
    text: str
    target: str
    # Bot API button style: "primary" | "success" | "danger" | None.
    style: str | None = None


ButtonRow = list[Btn]

STYLE_PRIMARY = "primary"
STYLE_SUCCESS = "success"
STYLE_DANGER = "danger"


def _is_url(target: str) -> bool:
    return target.startswith(("http://", "https://"))


def _normalize(rows) -> list[ButtonRow]:
    return [[Btn(*b) if not isinstance(b, Btn) else b for b in row] for row in rows]


def keyboard_from_rows(rows) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for row in _normalize(rows):
        builder.row(
            *(
                InlineKeyboardButton(text=b.text, url=b.target, style=b.style)
                if _is_url(b.target)
                else InlineKeyboardButton(text=b.text, callback_data=b.target, style=b.style)
                for b in row
            )
        )
    return builder.as_markup()


def split_button_rows(rows) -> tuple[InlineKeyboardMarkup, list[InputRichBlockButtons]]:
    """(full_keyboard, button_blocks): the rows as a classic keyboard, and
    as one InputRichBlockButtons per row ready to embed in a message."""
    normalized = _normalize(rows)
    full_keyboard = keyboard_from_rows(normalized)
    button_blocks = [
        InputRichBlockButtons(
            buttons=[
                RichMessageButton(text=b.text, url=b.target, style=b.style)
                if _is_url(b.target)
                else RichMessageButton(text=b.text, callback_data=b.target, style=b.style)
                for b in row
            ]
        )
        for row in normalized
    ]
    return full_keyboard, button_blocks


def apply_button_style(
    blocks: list[InputRichBlockUnion],
    rows,
    *,
    rich_buttons_enabled: bool,
    has_back_row: bool = True,
) -> tuple[list[InputRichBlockUnion], InlineKeyboardMarkup | None]:
    """Attaches a screen's buttons to its content blocks per the style
    preference. Returns (blocks, reply_markup)."""
    if not rows:
        return blocks, None

    full_keyboard, button_blocks = split_button_rows(rows)
    if not rich_buttons_enabled:
        return blocks, full_keyboard

    if not has_back_row or len(button_blocks) == 1:
        return [*blocks, InputRichBlockDivider(), *button_blocks], None

    *body_blocks, back_block = button_blocks
    return [
        *blocks,
        InputRichBlockDivider(),
        *body_blocks,
        InputRichBlockDivider(),
        back_block,
    ], None
