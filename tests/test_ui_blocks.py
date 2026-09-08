from aiogram.types import (
    InputRichBlockBlockQuotation,
    InputRichBlockButtons,
    InputRichBlockDivider,
    InputRichBlockParagraph,
    InputRichBlockSectionHeading,
    InputRichBlockTable,
    RichTextBold,
    RichTextCode,
)

from app.texts import ru
from app.ui.blocks import rich_blocks_from_legacy_text, strip_tags, table_block
from app.ui.buttons import Btn, apply_button_style, keyboard_from_rows, split_button_rows


def test_title_line_becomes_heading_with_a_single_divider():
    text = f"📊 <b>Статистика</b>\n{ru.SEPARATOR}\n\nСообщений: 5"
    blocks = rich_blocks_from_legacy_text(text)

    assert isinstance(blocks[0], InputRichBlockSectionHeading)
    assert blocks[0].text == ["📊 ", RichTextBold(text="Статистика")]
    assert isinstance(blocks[1], InputRichBlockDivider)
    # The template's own SEPARATOR right after the title must not add a
    # second divider.
    assert isinstance(blocks[2], InputRichBlockParagraph)
    assert len(blocks) == 3


def test_plain_text_without_a_title_has_no_heading():
    blocks = rich_blocks_from_legacy_text("Просто текст.")
    assert [type(b) for b in blocks] == [InputRichBlockParagraph]
    assert blocks[0].text == "Просто текст."


def test_separator_elsewhere_becomes_a_divider():
    blocks = rich_blocks_from_legacy_text(f"Первая\n{ru.SEPARATOR}\nВторая")
    assert [type(b) for b in blocks] == [
        InputRichBlockParagraph,
        InputRichBlockDivider,
        InputRichBlockParagraph,
    ]


def test_inline_code_and_blockquote():
    blocks = rich_blocks_from_legacy_text("Ключ: <code>sb_x</code>\n<blockquote>A\nB</blockquote>")
    assert blocks[0].text == ["Ключ: ", RichTextCode(text="sb_x")]
    assert isinstance(blocks[1], InputRichBlockBlockQuotation)
    assert [p.text for p in blocks[1].blocks] == ["A", "B"]


def test_strip_tags():
    assert strip_tags("<b>x</b> <i>y</i> <code>z</code>") == "x y z"


def test_table_block_marks_header_row():
    table = table_block(["Кто", "Сколько"], [["Ann", "<b>5</b>"]])
    assert isinstance(table, InputRichBlockTable)
    assert table.cells[0][0].is_header is True
    assert table.cells[1][0].is_header is False
    assert table.cells[1][1].text == RichTextBold(text="5")


# --- buttons ---


def _rows():
    return [
        [Btn("A", "a:1"), Btn("Site", "https://example.com", "primary")],
        [Btn("B", "b:1", "success")],
        [Btn("Назад", "back")],
    ]


def test_split_button_rows_maps_urls_and_styles():
    keyboard, blocks = split_button_rows(_rows())
    assert keyboard.inline_keyboard[0][1].url == "https://example.com"
    assert keyboard.inline_keyboard[0][1].style == "primary"
    assert keyboard.inline_keyboard[0][0].callback_data == "a:1"
    assert all(isinstance(b, InputRichBlockButtons) for b in blocks)
    assert blocks[0].buttons[1].url == "https://example.com"
    assert blocks[1].buttons[0].style == "success"
    assert blocks[2].buttons[0].callback_data == "back"


def test_old_style_keeps_a_classic_keyboard():
    blocks, keyboard = apply_button_style(
        [InputRichBlockParagraph(text="x")], _rows(), rich_buttons_enabled=False
    )
    assert len(blocks) == 1
    assert keyboard is not None and len(keyboard.inline_keyboard) == 3


def test_new_style_embeds_buttons_and_isolates_back_row():
    blocks, keyboard = apply_button_style(
        [InputRichBlockParagraph(text="x")], _rows(), rich_buttons_enabled=True
    )
    assert keyboard is None
    kinds = [type(b) for b in blocks]
    assert kinds == [
        InputRichBlockParagraph,
        InputRichBlockDivider,
        InputRichBlockButtons,
        InputRichBlockButtons,
        InputRichBlockDivider,
        InputRichBlockButtons,
    ]


def test_new_style_without_back_row_uses_one_divider():
    blocks, _ = apply_button_style(
        [InputRichBlockParagraph(text="x")],
        _rows(),
        rich_buttons_enabled=True,
        has_back_row=False,
    )
    assert [type(b) for b in blocks].count(InputRichBlockDivider) == 1


def test_no_rows_means_no_keyboard():
    blocks, keyboard = apply_button_style([], [], rich_buttons_enabled=True)
    assert blocks == [] and keyboard is None
    assert keyboard_from_rows([]).inline_keyboard == []


def test_plain_tuples_are_accepted_as_buttons():
    keyboard, _ = split_button_rows([[("A", "a")]])
    assert keyboard.inline_keyboard[0][0].text == "A"
