from datetime import UTC, datetime, time

from app.services.broadcast_service import (
    Content,
    content_from_message,
    format_days,
    next_recurring_run,
    parse_buttons,
    parse_datetime,
    parse_time,
)
from tests.fakes import make_message

TZ = "Europe/Moscow"
# Tuesday 2026-09-08 12:00 Moscow (09:00 UTC)
NOW = datetime(2026, 9, 8, 9, 0, tzinfo=UTC)


def test_parse_datetime_full_and_time_only():
    assert parse_datetime("15.09.2026 18:30", TZ, NOW) == datetime(2026, 9, 15, 15, 30, tzinfo=UTC)
    # today 13:00 Moscow is still ahead
    assert parse_datetime("13:00", TZ, NOW) == datetime(2026, 9, 8, 10, 0, tzinfo=UTC)
    # 09:00 Moscow already passed -> tomorrow
    assert parse_datetime("09:00", TZ, NOW) == datetime(2026, 9, 9, 6, 0, tzinfo=UTC)
    assert parse_datetime("01.01.2020 10:00", TZ, NOW) is None  # in the past
    assert parse_datetime("вчера", TZ, NOW) is None


def test_parse_time():
    assert parse_time("07:05") == time(7, 5)
    assert parse_time("25:00") is None


def test_next_recurring_run():
    # Tue now; Tue at 14:00 is later today
    assert next_recurring_run([1], time(14, 0), TZ, NOW) == datetime(2026, 9, 8, 11, 0, tzinfo=UTC)
    # Tue at 10:00 already passed -> next Tuesday
    assert next_recurring_run([1], time(10, 0), TZ, NOW) == datetime(2026, 9, 15, 7, 0, tzinfo=UTC)
    # Mon & Fri at 09:00 -> Friday
    assert next_recurring_run([0, 4], time(9, 0), TZ, NOW) == datetime(
        2026, 9, 11, 6, 0, tzinfo=UTC
    )
    assert next_recurring_run([], time(9, 0), TZ, NOW) is None


def test_format_days():
    assert format_days(list(range(7))) == "каждый день"
    assert format_days([4, 0]) == "Пн, Пт"


def test_parse_buttons():
    rows = parse_buttons("Сайт | https://example.com\nКанал — https://t.me/x\n")
    assert rows == [
        [{"text": "Сайт", "url": "https://example.com"}],
        [{"text": "Канал", "url": "https://t.me/x"}],
    ]
    assert parse_buttons("просто текст") is None


def test_content_from_text_and_photo_messages():
    text = make_message(
        chat_type="private",
        text="Привет *всем*",
        entities=[{"type": "bold", "offset": 7, "length": 6}],
    )
    content = content_from_message(text)
    assert content.type == "text" and content.text == "Привет *всем*"
    assert content.entities[0]["type"] == "bold"
    assert content.message_entities()[0].length == 6

    photo = make_message(
        chat_type="private",
        text=None,
        content_type_payload={
            "photo": [
                {"file_id": "small", "file_unique_id": "a", "width": 1, "height": 1},
                {"file_id": "big", "file_unique_id": "b", "width": 9, "height": 9},
            ],
            "caption": "подпись",
        },
    )
    content = content_from_message(photo)
    assert content.type == "photo" and content.file_id == "big" and content.text == "подпись"
    assert content.is_media

    sticker = make_message(
        chat_type="private",
        text=None,
        content_type_payload={
            "sticker": {
                "file_id": "s",
                "file_unique_id": "s",
                "type": "regular",
                "width": 1,
                "height": 1,
                "is_animated": False,
                "is_video": False,
            }
        },
    )
    assert content_from_message(sticker) is None


def test_content_roundtrip_and_markup():
    c = Content(type="text", text="x", buttons=[[{"text": "A", "url": "https://a"}]])
    back = Content.from_json(c.to_json())
    assert back == c
    markup = back.reply_markup()
    assert markup.inline_keyboard[0][0].url == "https://a"
    assert Content(type="text", text="x").reply_markup() is None


def test_plain_message_with_markdown_becomes_html():
    msg = make_message(chat_type="private", text="Привет, **мир**! _ок_")
    content = content_from_message(msg)
    assert content.parse_mode == "HTML"
    assert content.text == "Привет, <b>мир</b>! <i>ок</i>"
    assert content.entities is None


def test_native_formatting_wins_over_markdown():
    msg = make_message(
        chat_type="private",
        text="*not markdown* bold",
        entities=[{"type": "bold", "offset": 15, "length": 4}],
    )
    content = content_from_message(msg)
    assert content.parse_mode is None and content.text == "*not markdown* bold"
    assert content.entities[0]["type"] == "bold"


def test_plain_text_without_markup_is_untouched():
    msg = make_message(chat_type="private", text="a < b & c")
    content = content_from_message(msg)
    assert content.parse_mode is None and content.text == "a < b & c"


def test_caption_markdown():
    photo = make_message(
        chat_type="private",
        text=None,
        content_type_payload={
            "photo": [{"file_id": "big", "file_unique_id": "b", "width": 9, "height": 9}],
            "caption": "||секрет||",
        },
    )
    content = content_from_message(photo)
    assert content.parse_mode == "HTML" and content.text == "<tg-spoiler>секрет</tg-spoiler>"
