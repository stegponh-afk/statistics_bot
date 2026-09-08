"""«Отчёты»: the numbers a chat produced, pushed to its admins instead of
waiting to be asked for.

A report always covers whole days that are already over — yesterday for a
daily digest, the previous seven days for a weekly one — so it never
changes after it is sent. `digest_last_day` records the local day a chat
was reported on, which is what keeps the every-few-minutes job from
sending the same report twice.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat, ChatAdmin, User
from app.services import channel_stats, stats_service
from app.services.user_service import get_users_by_telegram_ids
from app.texts import ru
from app.ui import Btn, Screen, send
from app.utils import display_name, get_zone

logger = logging.getLogger(__name__)

DAILY = "daily"
WEEKLY = "weekly"
PERIODS = (DAILY, WEEKLY)
# Weekly reports go out on Monday and cover the week that just ended.
WEEKLY_WEEKDAY = 0

_MEDALS = ("🥇", "🥈", "🥉")


@dataclass(frozen=True)
class Window:
    """The reported range and the one before it, for the comparison."""

    day_from: date
    day_to: date
    prev_from: date
    prev_to: date


def window(period: str, today: date) -> Window:
    if period == WEEKLY:
        day_to = today - timedelta(days=1)
        day_from = today - timedelta(days=7)
        return Window(day_from, day_to, day_from - timedelta(days=7), day_to - timedelta(days=7))
    yesterday = today - timedelta(days=1)
    before = today - timedelta(days=2)
    return Window(yesterday, yesterday, before, before)


# --- scheduling -------------------------------------------------------------


def local_now(chat: Chat, now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)).astimezone(get_zone(chat.timezone))


def is_due(chat: Chat, now: datetime | None = None) -> bool:
    """True when this chat's report for the current local day is owed."""
    if not chat.digest_enabled:
        return False
    here = local_now(chat, now)
    if chat.digest_period == WEEKLY and here.weekday() != WEEKLY_WEEKDAY:
        return False
    if chat.digest_last_day == here.date():
        return False
    return here.strftime("%H:%M") >= (chat.digest_time or "10:00")


async def due_chats(session: AsyncSession, now: datetime | None = None) -> list[Chat]:
    chats = await session.scalars(select(Chat).where(Chat.digest_enabled.is_(True)))
    return [c for c in chats if c.is_active and is_due(c, now)]


# --- the report -------------------------------------------------------------


def _delta_line(current: int, previous: int) -> str:
    if previous <= 0:
        return ru.DIGEST_NO_COMPARISON if current else ""
    pct = (current - previous) / previous * 100
    arrow = "▲" if pct > 0 else ("▼" if pct < 0 else "＝")
    return ru.DIGEST_COMPARISON.format(previous=previous, arrow=arrow, pct=abs(pct))


async def build_screen(session: AsyncSession, chat: Chat, today: date) -> Screen:
    period = chat.digest_period if chat.digest_period in PERIODS else DAILY
    w = window(period, today)
    label = ru.DIGEST_PERIOD_WEEK if period == WEEKLY else ru.DIGEST_PERIOD_DAY
    body = (
        await _channel_body(session, chat, w)
        if chat.is_channel
        else await _group_body(session, chat, w)
    )
    text = (
        ru.DIGEST_HEADER.format(
            icon="📣" if chat.is_channel else "👥",
            title=chat.title or chat.telegram_id,
            period=label,
            dates=_dates(w),
        )
        + body
    )
    rows = [
        [Btn(ru.BTN_CHAT_STATS, f"chat:{chat.id}:stats")],
        [Btn(ru.BTN_DIGEST_SETTINGS, f"chat:{chat.id}:digest")],
    ]
    return Screen(text, rows=rows, has_back_row=False)


def _dates(w: Window) -> str:
    if w.day_from == w.day_to:
        return w.day_from.strftime("%d.%m.%Y")
    return f"{w.day_from.strftime('%d.%m')} — {w.day_to.strftime('%d.%m.%Y')}"


async def _members_line(session: AsyncSession, chat: Chat, w: Window) -> str:
    flow = await channel_stats.flow(session, chat.telegram_id, w.day_from, w.day_to)
    total = await channel_stats.count_on_or_before(session, chat.telegram_id, w.day_to)
    if total is None:
        total = chat.member_count
    return ru.DIGEST_MEMBERS.format(
        total=total if total is not None else "—",
        joins=flow.joins,
        leaves=flow.leaves,
        net=f"{flow.net:+d}",
    )


async def _group_body(session: AsyncSession, chat: Chat, w: Window) -> str:
    messages = await stats_service.messages_count(session, chat.telegram_id, w.day_from, w.day_to)
    previous = await stats_service.messages_count(session, chat.telegram_id, w.prev_from, w.prev_to)
    active = await stats_service.active_users(session, chat.telegram_id, w.day_from, w.day_to)
    body = ru.DIGEST_MESSAGES.format(
        count=messages, comparison=_delta_line(messages, previous), active=active
    )
    body += await _members_line(session, chat, w)

    top = await stats_service.top_users(session, chat.telegram_id, w.day_from, w.day_to, limit=3)
    if top:
        users = await get_users_by_telegram_ids(session, [uid for uid, _ in top])
        lines = []
        for i, (uid, n) in enumerate(top):
            u = users.get(uid)
            name = display_name(u.full_name, u.username, uid) if u else f"id:{uid}"
            lines.append(ru.DIGEST_TOP_USER_ROW.format(medal=_MEDALS[i], name=name, count=n))
        body += ru.DIGEST_TOP_USERS.format(rows="\n".join(lines))

    words = await stats_service.top_words(session, chat.telegram_id, w.day_from, w.day_to, limit=5)
    if words:
        body += ru.DIGEST_WORDS.format(words=", ".join(word for word, _ in words))
    if not messages and not active:
        body += ru.DIGEST_QUIET
    return body


async def _channel_body(session: AsyncSession, chat: Chat, w: Window) -> str:
    body = await _members_line(session, chat, w)
    posts = await channel_stats.posts_count(session, chat.telegram_id, w.day_from, w.day_to)
    previous = await channel_stats.posts_count(session, chat.telegram_id, w.prev_from, w.prev_to)
    reactions = await channel_stats.reactions(session, chat.telegram_id, w.day_from, w.day_to)
    body += ru.DIGEST_POSTS.format(
        count=posts,
        comparison=_delta_line(posts, previous),
        average=f"{reactions.average:.1f}",
    )
    if reactions.best_message_id is not None:
        body += ru.DIGEST_BEST_POST.format(
            total=reactions.best_total,
            link=channel_stats.post_link(chat, reactions.best_message_id),
        )
    if not posts:
        body += ru.DIGEST_NO_POSTS
    return body


# --- delivery ---------------------------------------------------------------


async def recipients(session: AsyncSession, chat: Chat) -> list[User]:
    """Admins of the chat who can be DMed at all."""
    result = await session.scalars(
        select(User)
        .join(ChatAdmin, ChatAdmin.user_id == User.id)
        .where(ChatAdmin.chat_id == chat.id, User.started_bot.is_(True))
    )
    return list(result)


async def send_digest(
    bot: Bot, session: AsyncSession, chat: Chat, now: datetime | None = None
) -> int:
    """Builds and DMs one chat's report. Returns how many admins got it.
    The chat is marked as reported either way — a report nobody can
    receive must not be retried every few minutes."""
    today = local_now(chat, now).date()
    screen = await build_screen(session, chat, today)
    delivered = 0
    for user in await recipients(session, chat):
        try:
            await send(bot, user.telegram_id, screen, rich_buttons=user.rich_buttons_enabled)
            delivered += 1
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            logger.info("digest for %s not delivered to %s: %s", chat.telegram_id, user.id, e)
    chat.digest_last_day = today
    await session.commit()
    logger.info("digest for %s sent to %d admins", chat.telegram_id, delivered)
    return delivered
