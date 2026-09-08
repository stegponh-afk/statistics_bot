"""Broadcasts: the message content model, scheduling arithmetic and CRUD.
Delivery lives in broadcast_delivery."""

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, MessageEntity
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    ApiKey,
    Broadcast,
    BroadcastKind,
    BroadcastStatus,
    BroadcastTarget,
    BroadcastTargetKind,
    Chat,
    User,
)
from app.services.markdown import has_markup, markdown_to_html
from app.utils import ensure_aware, get_zone

MEDIA_TYPES = ("photo", "video", "document", "animation", "audio", "voice")
WEEKDAY_LABELS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")

_BUTTON_LINE_RE = re.compile(r"^\s*(.+?)\s*[|—-]\s*(https?://\S+)\s*$")


# --- content --------------------------------------------------------------


@dataclass
class Content:
    type: str  # "text" or one of MEDIA_TYPES
    text: str | None = None  # text, or caption for media
    entities: list[dict] | None = None
    file_id: str | None = None
    buttons: list[list[dict]] = field(default_factory=list)  # [[{"text","url"}]]
    # "HTML" when `text` was produced from markdown (then entities is None);
    # None when `entities` carry the formatting the admin applied in Telegram.
    parse_mode: str | None = None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Content":
        return cls(**data)

    def message_entities(self) -> list[MessageEntity] | None:
        if not self.entities:
            return None
        return [MessageEntity.model_validate(e) for e in self.entities]

    def reply_markup(self) -> InlineKeyboardMarkup | None:
        if not self.buttons:
            return None
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=b["text"], url=b["url"]) for b in row]
                for row in self.buttons
            ]
        )

    @property
    def is_media(self) -> bool:
        return self.type in MEDIA_TYPES


def content_from_message(message: Message) -> Content | None:
    """What of an admin's message can be re-sent later. None = unsupported."""
    if message.text is not None:
        return _with_markdown(Content(type="text"), message.text, message.entities)
    caption = message.caption
    if message.photo:
        file_id = message.photo[-1].file_id
        kind = "photo"
    elif message.video:
        file_id, kind = message.video.file_id, "video"
    elif message.animation:
        file_id, kind = message.animation.file_id, "animation"
    elif message.document:
        file_id, kind = message.document.file_id, "document"
    elif message.audio:
        file_id, kind = message.audio.file_id, "audio"
    elif message.voice:
        file_id, kind = message.voice.file_id, "voice"
    else:
        return None
    content = Content(type=kind, file_id=file_id)
    if caption is None:
        return content
    return _with_markdown(content, caption, message.caption_entities)


def _with_markdown(content: Content, text: str, entities) -> Content:
    """Formatting the admin applied in Telegram arrives as entities and is
    kept as is; a plain message may instead use markdown (see
    services.markdown), which becomes HTML."""
    dumped = [e.model_dump(exclude_none=True) for e in entities or []] or None
    if dumped is None and has_markup(text):
        content.text = markdown_to_html(text)
        content.parse_mode = "HTML"
    else:
        content.text = text
        content.entities = dumped
    return content


def parse_buttons(text: str) -> list[list[dict]] | None:
    """One button per line: `Текст | https://…` (also `-` or `—` as the
    separator). None if any line doesn't parse."""
    rows: list[list[dict]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        m = _BUTTON_LINE_RE.match(line)
        if not m:
            return None
        rows.append([{"text": m.group(1)[:64], "url": m.group(2)}])
    return rows


# --- scheduling ----------------------------------------------------------------


def parse_datetime(text: str, tz_name: str, now: datetime | None = None) -> datetime | None:
    """'ДД.ММ.ГГГГ ЧЧ:ММ' or just 'ЧЧ:ММ' (today, or tomorrow if passed).
    Returns an aware UTC datetime in the future, else None."""
    zone = get_zone(tz_name)
    now_local = ensure_aware(now or datetime.now(UTC)).astimezone(zone)
    text = text.strip()
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%y %H:%M"):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        local = parsed.replace(tzinfo=zone)
        return local.astimezone(UTC) if local > now_local else None
    try:
        t = datetime.strptime(text, "%H:%M").time()
    except ValueError:
        return None
    candidate = datetime.combine(now_local.date(), t, tzinfo=zone)
    if candidate <= now_local:
        candidate += timedelta(days=1)
    return candidate.astimezone(UTC)


def parse_time(text: str) -> time | None:
    try:
        return datetime.strptime(text.strip(), "%H:%M").time()
    except ValueError:
        return None


def next_recurring_run(
    days: list[int], at: time, tz_name: str, now: datetime | None = None
) -> datetime | None:
    """The next moment (UTC) that falls on one of `days` (0=Mon) at `at`
    local time, strictly after `now`."""
    if not days:
        return None
    zone = get_zone(tz_name)
    now_local = ensure_aware(now or datetime.now(UTC)).astimezone(zone)
    for offset in range(0, 8):
        day: date = now_local.date() + timedelta(days=offset)
        if day.weekday() not in days:
            continue
        candidate = datetime.combine(day, at, tzinfo=zone)
        if candidate > now_local:
            return candidate.astimezone(UTC)
    return None


def format_days(days: list[int]) -> str:
    if sorted(days) == list(range(7)):
        return "каждый день"
    return ", ".join(WEEKDAY_LABELS[d] for d in sorted(days))


def format_local(dt: datetime | None, tz_name: str) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(get_zone(tz_name)).strftime("%d.%m.%Y %H:%M")


# --- CRUD ----------------------------------------------------------------------


async def create_broadcast(
    session: AsyncSession,
    owner: User,
    *,
    kind: BroadcastKind,
    content: Content,
    chat_ids: list[int],
    bot_key_ids: list[int],
    tz_name: str,
    scheduled_at: datetime | None = None,
    recur_days: list[int] | None = None,
    recur_time: time | None = None,
) -> Broadcast:
    now = datetime.now(UTC)
    if kind == BroadcastKind.NOW:
        next_run = now
    elif kind == BroadcastKind.ONCE:
        next_run = scheduled_at
    else:
        next_run = next_recurring_run(recur_days or [], recur_time, tz_name, now)
    broadcast = Broadcast(
        owner_user_id=owner.id,
        kind=kind.value,
        status=BroadcastStatus.SCHEDULED.value,
        content=content.to_json(),
        scheduled_at=scheduled_at,
        recur_days=",".join(str(d) for d in sorted(recur_days)) if recur_days else None,
        recur_time=recur_time.strftime("%H:%M") if recur_time else None,
        timezone=tz_name,
        next_run_at=next_run,
    )
    session.add(broadcast)
    await session.flush()
    session.add_all(
        [
            BroadcastTarget(
                broadcast_id=broadcast.id, kind=BroadcastTargetKind.CHAT.value, target_id=cid
            )
            for cid in chat_ids
        ]
        + [
            BroadcastTarget(
                broadcast_id=broadcast.id, kind=BroadcastTargetKind.BOT.value, target_id=kid
            )
            for kid in bot_key_ids
        ]
    )
    await session.commit()
    await session.refresh(broadcast)
    return broadcast


async def list_broadcasts(session: AsyncSession, owner: User) -> list[Broadcast]:
    result = await session.scalars(
        select(Broadcast)
        .where(
            Broadcast.owner_user_id == owner.id,
            Broadcast.status != BroadcastStatus.CANCELLED.value,
        )
        .order_by(Broadcast.created_at.desc(), Broadcast.id.desc())
    )
    return list(result)


async def get_owned_broadcast(
    session: AsyncSession, owner: User, broadcast_id: int
) -> Broadcast | None:
    broadcast = await session.get(Broadcast, broadcast_id)
    if broadcast is None or broadcast.owner_user_id != owner.id:
        return None
    return broadcast


async def targets(session: AsyncSession, broadcast: Broadcast) -> tuple[list[Chat], list[ApiKey]]:
    rows = list(
        await session.scalars(
            select(BroadcastTarget).where(BroadcastTarget.broadcast_id == broadcast.id)
        )
    )
    chat_ids = [r.target_id for r in rows if r.kind == BroadcastTargetKind.CHAT.value]
    key_ids = [r.target_id for r in rows if r.kind == BroadcastTargetKind.BOT.value]
    chats = (
        list(await session.scalars(select(Chat).where(Chat.id.in_(chat_ids)))) if chat_ids else []
    )
    keys = (
        list(await session.scalars(select(ApiKey).where(ApiKey.id.in_(key_ids)))) if key_ids else []
    )
    return chats, keys


async def set_status(session: AsyncSession, broadcast: Broadcast, status: BroadcastStatus) -> None:
    broadcast.status = status.value
    if status == BroadcastStatus.SCHEDULED and broadcast.kind == BroadcastKind.RECURRING.value:
        broadcast.next_run_at = next_recurring_run(
            broadcast.recur_days_list, parse_time(broadcast.recur_time), broadcast.timezone
        )
    await session.commit()


async def due_broadcasts(session: AsyncSession, now: datetime | None = None) -> list[Broadcast]:
    now = now or datetime.now(UTC)
    result = await session.scalars(
        select(Broadcast)
        .where(
            Broadcast.status == BroadcastStatus.SCHEDULED.value,
            Broadcast.next_run_at.is_not(None),
            Broadcast.next_run_at <= now,
        )
        .order_by(Broadcast.next_run_at)
    )
    return list(result)


def advance_after_run(broadcast: Broadcast, now: datetime | None = None) -> None:
    """Moves a broadcast past a run: recurring ones get their next slot,
    the others are done."""
    now = ensure_aware(now) if now else datetime.now(UTC)
    broadcast.last_run_at = now
    broadcast.runs_count += 1
    if broadcast.kind == BroadcastKind.RECURRING.value:
        broadcast.next_run_at = next_recurring_run(
            broadcast.recur_days_list, parse_time(broadcast.recur_time), broadcast.timezone, now
        )
    else:
        broadcast.next_run_at = None
        broadcast.status = BroadcastStatus.DONE.value
