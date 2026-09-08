"""Test doubles: a FakeBot that records every API call and can be
programmed with getChatMember/getChatAdministrators answers, plus helpers
that build real aiogram Message/CallbackQuery objects bound to it."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from aiogram.methods import TelegramMethod
from aiogram.types import CallbackQuery, ChatMember, Message, User


class FakeClock:
    def __init__(self, start: float = 1_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeBot:
    """Quacks like aiogram.Bot for the calls this project makes.

    Direct method calls (bot.send_message(...)) and aiogram's internal
    `bot(method)` path (message.edit_text(...) etc.) both end up in
    `self.calls` as (method_name, kwargs)."""

    def __init__(self, bot_id: int = 999_000) -> None:
        self.id = bot_id
        self.calls: list[tuple[str, dict[str, Any]]] = []
        # (chat_id, user_id) -> ChatMember | Exception
        self.members: dict[tuple[int, int], ChatMember | Exception] = {}
        # chat_id -> list[ChatMember] | Exception
        self.administrators: dict[int, list[ChatMember] | Exception] = {}
        self.member_counts: dict[int, int] = {}
        self.invite_links: dict[int, str] = {}
        # method name -> Exception to raise on the next call of that method
        self.fail_next: dict[str, Exception] = {}
        self._message_id = 100

    def _record(self, name: str, **kwargs: Any) -> None:
        self.calls.append((name, kwargs))

    def _maybe_fail(self, name: str) -> None:
        exc = self.fail_next.pop(name, None)
        if exc is not None:
            raise exc

    def calls_named(self, name: str) -> list[dict[str, Any]]:
        return [kw for n, kw in self.calls if n == name]

    def _next_message(self, chat_id: int, **extra: Any) -> Message:
        self._message_id += 1
        extra.setdefault("message_id", self._message_id)
        return make_message(chat_id=chat_id, bot=self, from_bot=True, **extra)

    # --- chat info -----------------------------------------------------

    async def get_chat_member(self, chat_id: int, user_id: int) -> ChatMember:
        self._record("get_chat_member", chat_id=chat_id, user_id=user_id)
        self._maybe_fail("get_chat_member")
        result = self.members.get((chat_id, user_id))
        if isinstance(result, Exception):
            raise result
        if result is None:
            raise KeyError(f"no programmed member for {(chat_id, user_id)}")
        return result

    async def get_chat_administrators(self, chat_id: int) -> list[ChatMember]:
        self._record("get_chat_administrators", chat_id=chat_id)
        self._maybe_fail("get_chat_administrators")
        result = self.administrators.get(chat_id, [])
        if isinstance(result, Exception):
            raise result
        return result

    async def get_chat_member_count(self, chat_id: int) -> int:
        self._record("get_chat_member_count", chat_id=chat_id)
        self._maybe_fail("get_chat_member_count")
        return self.member_counts.get(chat_id, 0)

    async def get_chat(self, chat_id: int) -> Any:
        self._record("get_chat", chat_id=chat_id)
        self._maybe_fail("get_chat")
        from aiogram.types import ChatFullInfo

        return ChatFullInfo.model_validate(
            {
                "id": chat_id,
                "type": "channel" if chat_id < 0 else "private",
                "title": "Chat",
                "accent_color_id": 0,
                "max_reaction_count": 1,
                "accepted_gift_types": {
                    "unlimited_gifts": False,
                    "limited_gifts": False,
                    "unique_gifts": False,
                    "premium_subscription": False,
                    "gifts_from_channels": False,
                },
                "invite_link": self.invite_links.get(chat_id),
            }
        )

    async def export_chat_invite_link(self, chat_id: int) -> str:
        self._record("export_chat_invite_link", chat_id=chat_id)
        self._maybe_fail("export_chat_invite_link")
        return f"https://t.me/+exported{abs(chat_id)}"

    # --- sending / editing ---------------------------------------------

    async def send_message(self, chat_id: int, text: str, **kwargs: Any) -> Message:
        self._record("send_message", chat_id=chat_id, text=text, **kwargs)
        self._maybe_fail("send_message")
        return self._next_message(chat_id, text=text)

    async def send_rich_message(self, chat_id: int, **kwargs: Any) -> Message:
        self._record("send_rich_message", chat_id=chat_id, **kwargs)
        self._maybe_fail("send_rich_message")
        params = kwargs.get("ephemeral_message_parameters")
        if params is not None:
            return self._next_message(
                chat_id, ephemeral_message_id=7, receiver_user_id=params.receiver_user_id
            )
        return self._next_message(chat_id)

    async def edit_ephemeral_message_text(self, **kwargs: Any) -> bool:
        self._record("edit_ephemeral_message_text", **kwargs)
        self._maybe_fail("edit_ephemeral_message_text")
        return True

    async def delete_message(self, chat_id: int, message_id: int, **kwargs: Any) -> bool:
        self._record("delete_message", chat_id=chat_id, message_id=message_id)
        self._maybe_fail("delete_message")
        return True

    async def answer_callback_query(self, callback_query_id: str, **kwargs: Any) -> bool:
        self._record("answer_callback_query", callback_query_id=callback_query_id, **kwargs)
        return True

    # --- aiogram's internal call path -----------------------------------

    async def __call__(self, method: TelegramMethod, *args: Any, **kwargs: Any) -> Any:
        name = _snake(type(method).__name__)
        payload = method.model_dump(exclude_none=True)
        self._record(name, **payload)
        self._maybe_fail(name)
        if name in ("send_message", "send_rich_message"):
            return self._next_message(payload["chat_id"])
        if name == "edit_message_text":
            return self._next_message(payload["chat_id"], message_id=payload.get("message_id", 1))
        return True


def _snake(name: str) -> str:
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


def make_user(user_id: int = 42, *, is_bot: bool = False, name: str = "Ann") -> dict:
    return {"id": user_id, "is_bot": is_bot, "first_name": name, "username": f"u{user_id}"}


def make_message(
    *,
    chat_id: int = -100_1,
    chat_type: str = "supergroup",
    message_id: int = 10,
    user_id: int | None = 42,
    text: str | None = "hello",
    content_type_payload: dict | None = None,
    ephemeral_message_id: int | None = None,
    receiver_user_id: int | None = None,
    sender_chat_id: int | None = None,
    from_bot: bool = False,
    date: datetime | None = None,
    bot: FakeBot | None = None,
    **extra: Any,
) -> Message:
    payload: dict[str, Any] = {
        "message_id": message_id,
        "date": int((date or datetime.now(UTC)).timestamp()),
        "chat": {"id": chat_id, "type": chat_type, "title": "Chat"}
        if chat_type != "private"
        else {"id": chat_id, "type": "private", "first_name": "Ann"},
    }
    if user_id is not None:
        payload["from"] = make_user(user_id, is_bot=from_bot)
    if text is not None:
        payload["text"] = text
    if content_type_payload:
        payload.update(content_type_payload)
    if ephemeral_message_id is not None:
        payload["ephemeral_message_id"] = ephemeral_message_id
        payload["message_id"] = 0
    if receiver_user_id is not None:
        payload["receiver_user"] = make_user(receiver_user_id)
    if sender_chat_id is not None:
        payload["sender_chat"] = {"id": sender_chat_id, "type": "channel", "title": "Sender"}
    payload.update(extra)
    message = Message.model_validate(payload, context={"bot": bot} if bot else None)
    return message


def make_callback(
    message: Message, data: str, *, user_id: int = 42, bot: FakeBot | None = None
) -> CallbackQuery:
    payload = {
        "id": "cb1",
        "from": make_user(user_id),
        "chat_instance": "ci",
        "data": data,
        "message": message.model_dump(exclude_none=True),
    }
    return CallbackQuery.model_validate(payload, context={"bot": bot} if bot else None)


def tg_user(user_id: int, name: str = "Ann", *, is_bot: bool = False) -> User:
    return User.model_validate(make_user(user_id, is_bot=is_bot, name=name))
