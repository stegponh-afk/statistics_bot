"""The statistics screens, shared by /stats in groups (ephemeral) and the
chat card in private chat. Callers supply how tab buttons are addressed."""

from collections.abc import Callable
from datetime import timedelta

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Chat
from app.services import channel_stats, chat_service, stats_service
from app.services.user_service import get_users_by_telegram_ids
from app.texts import ru
from app.ui import Btn, Screen
from app.utils import display_name, local_today

TABS = ("overview", "users", "words", "hours")
CHANNEL_TABS = ("overview", "dynamics", "posts", "hours")
_MEDALS = ("🥇", "🥈", "🥉", "4.", "5.")
_BAR = "▇"
_BAR_WIDTH = 10

TabTarget = Callable[[str], str]


def _tab_rows(
    target: TabTarget, current: str, back: Btn | None, tabs_set: tuple[str, ...] = TABS
) -> list[list[Btn]]:
    labels = {
        "overview": ru.BTN_STATS_OVERVIEW,
        "users": ru.BTN_STATS_USERS,
        "words": ru.BTN_STATS_WORDS,
        "hours": ru.BTN_STATS_HOURS,
        "dynamics": ru.BTN_STATS_DYNAMICS,
        "posts": ru.BTN_STATS_POSTS,
    }
    tabs = [
        Btn(labels[tab], target(tab), "primary" if tab == current else None)
        for tab in tabs_set
        if tab != current
    ]
    rows = [tabs, [Btn(ru.BTN_REFRESH, target(current))]]
    if back is not None:
        rows.append([back])
    return rows


def _tz_name(chat: Chat) -> str:
    from config import settings

    return chat.timezone or settings.default_timezone


async def overview_screen(
    bot: Bot, session: AsyncSession, chat: Chat, *, target: TabTarget, back: Btn | None
) -> Screen:
    today = local_today(chat.timezone)
    data = await stats_service.overview(session, chat.telegram_id, today)
    members = await chat_service.get_member_count(bot, session, chat) if chat.is_active else None
    flow_today = await channel_stats.flow(session, chat.telegram_id, today, today)
    text = ru.STATS_OVERVIEW.format(
        title=chat.title or chat.telegram_id,
        today=data.today,
        week=data.week,
        month=data.month,
        active_week=data.active_week,
        members_line=(
            ru.STATS_MEMBERS_FLOW_LINE.format(
                count=members, joins=flow_today.joins, leaves=flow_today.leaves
            )
            if members is not None
            else ""
        ),
        tz=_tz_name(chat),
    )
    return Screen(text, rows=_tab_rows(target, "overview", back), has_back_row=back is not None)


def _period(chat: Chat):
    today = local_today(chat.timezone)
    return today - timedelta(days=stats_service.WEEK - 1), today


async def top_users_screen(
    session: AsyncSession, chat: Chat, *, target: TabTarget, back: Btn | None
) -> Screen:
    day_from, day_to = _period(chat)
    rows = await stats_service.top_users(session, chat.telegram_id, day_from, day_to)
    users = await get_users_by_telegram_ids(session, [uid for uid, _ in rows])
    lines = [ru.STATS_TITLE.format(title=chat.title or chat.telegram_id), ru.SEPARATOR]
    lines.append(ru.STATS_TOP_USERS_TITLE)
    if not rows:
        lines.append(ru.STATS_EMPTY)
    for i, (uid, count) in enumerate(rows):
        u = users.get(uid)
        name = display_name(u.full_name, u.username, uid) if u else f"id:{uid}"
        lines.append(ru.STATS_USER_ROW.format(medal=_MEDALS[i], name=name, count=count))
    return Screen(
        "\n".join(lines), rows=_tab_rows(target, "users", back), has_back_row=back is not None
    )


async def top_words_screen(
    session: AsyncSession, chat: Chat, *, target: TabTarget, back: Btn | None
) -> Screen:
    day_from, day_to = _period(chat)
    rows = await stats_service.top_words(session, chat.telegram_id, day_from, day_to)
    lines = [ru.STATS_TITLE.format(title=chat.title or chat.telegram_id), ru.SEPARATOR]
    lines.append(ru.STATS_TOP_WORDS_TITLE)
    if not rows:
        lines.append(ru.STATS_EMPTY)
    for i, (word, count) in enumerate(rows, start=1):
        lines.append(ru.STATS_WORD_ROW.format(n=i, word=word, count=count))
    return Screen(
        "\n".join(lines), rows=_tab_rows(target, "words", back), has_back_row=back is not None
    )


def hour_rows(slots: list[int], bucket: int = 2) -> list[tuple[str, str, int]]:
    """(label, bar, count) per `bucket`-hour range, bars scaled to the max."""
    buckets = [sum(slots[i : i + bucket]) for i in range(0, 24, bucket)]
    peak = max(buckets) or 1
    out = []
    for i, count in enumerate(buckets):
        start = i * bucket
        end = start + bucket - 1
        label = f"{start:02d}–{end:02d}"
        bar = _BAR * max(1 if count else 0, round(count / peak * _BAR_WIDTH))
        out.append((label, bar or "·", count))
    return out


async def hours_screen(
    session: AsyncSession, chat: Chat, *, target: TabTarget, back: Btn | None
) -> Screen:
    day_from, day_to = _period(chat)
    slots = await stats_service.activity_by_hour(session, chat.telegram_id, day_from, day_to)
    lines = [ru.STATS_TITLE.format(title=chat.title or chat.telegram_id), ru.SEPARATOR]
    lines.append(ru.STATS_HOURS_TITLE)
    if not any(slots):
        lines.append(ru.STATS_EMPTY)
    else:
        for label, bar, count in hour_rows(slots):
            lines.append(ru.STATS_HOURS_ROW.format(label=label, bar=bar, count=count))
    return Screen(
        "\n".join(lines), rows=_tab_rows(target, "hours", back), has_back_row=back is not None
    )


# --- channels ------------------------------------------------------------------


async def channel_overview_screen(
    bot: Bot, session: AsyncSession, chat: Chat, *, target: TabTarget, back: Btn | None
) -> Screen:
    today = local_today(chat.timezone)
    yesterday = today - timedelta(days=1)
    members = await chat_service.get_member_count(bot, session, chat) if chat.is_active else None
    f_today = await channel_stats.flow(session, chat.telegram_id, today, today)
    f_yday = await channel_stats.flow(session, chat.telegram_id, yesterday, yesterday)
    week_ago = await channel_stats.count_on_or_before(
        session, chat.telegram_id, today - timedelta(days=7)
    )
    month_ago = await channel_stats.count_on_or_before(
        session, chat.telegram_id, today - timedelta(days=30)
    )
    posts_today = await channel_stats.posts_count(session, chat.telegram_id, today, today)
    posts_week = await channel_stats.posts_count(
        session, chat.telegram_id, today - timedelta(days=6), today
    )
    posts_month = await channel_stats.posts_count(
        session, chat.telegram_id, today - timedelta(days=29), today
    )
    reactions = await channel_stats.reactions(
        session, chat.telegram_id, today - timedelta(days=29), today
    )
    best = "—"
    if reactions.best_message_id is not None:
        best = ru.STATS_BEST_POST.format(
            total=reactions.best_total,
            link=channel_stats.post_link(chat, reactions.best_message_id),
        )
    comments_line = ""
    if chat.linked_chat_tg_id:
        comments = await channel_stats.posts_count(
            session, chat.linked_chat_tg_id, today - timedelta(days=6), today
        )
        comments_line = ru.STATS_COMMENTS_LINE.format(count=comments)
    text = ru.STATS_CHANNEL_OVERVIEW.format(
        title=chat.title or chat.telegram_id,
        members=members if members is not None else "?",
        today_joins=f_today.joins,
        today_leaves=f_today.leaves,
        today_net=f"{f_today.net:+d}",
        yday_joins=f_yday.joins,
        yday_leaves=f_yday.leaves,
        yday_net=f"{f_yday.net:+d}",
        week=channel_stats.growth_label(members, week_ago),
        month=channel_stats.growth_label(members, month_ago),
        posts_today=posts_today,
        posts_week=posts_week,
        posts_month=posts_month,
        avg_reactions=f"{reactions.average:.1f}",
        best=best,
        comments_line=comments_line,
        tz=_tz_name(chat),
    )
    return Screen(
        text,
        rows=_tab_rows(target, "overview", back, CHANNEL_TABS),
        has_back_row=back is not None,
    )


async def channel_dynamics_screen(
    session: AsyncSession, chat: Chat, *, target: TabTarget, back: Btn | None
) -> Screen:
    today = local_today(chat.timezone)
    rows = await channel_stats.daily_rows(session, chat.telegram_id, today)
    lines = [ru.STATS_TITLE.format(title=chat.title or chat.telegram_id), ru.SEPARATOR]
    lines.append(ru.STATS_DYNAMICS_TITLE)
    lines.append(ru.STATS_DYNAMICS_HEADER)
    for r in reversed(rows):
        lines.append(
            ru.STATS_DYNAMICS_ROW.format(
                day=r.day.strftime("%d.%m"),
                subscribers=r.subscribers if r.subscribers is not None else "—",
                joins=r.joins,
                leaves=r.leaves,
                posts=r.posts,
            )
        )
    return Screen(
        "\n".join(lines),
        rows=_tab_rows(target, "dynamics", back, CHANNEL_TABS),
        has_back_row=back is not None,
    )


async def channel_posts_screen(
    session: AsyncSession, chat: Chat, *, target: TabTarget, back: Btn | None
) -> Screen:
    today = local_today(chat.timezone)
    top = await channel_stats.top_posts(
        session, chat.telegram_id, today - timedelta(days=29), today
    )
    lines = [ru.STATS_TITLE.format(title=chat.title or chat.telegram_id), ru.SEPARATOR]
    lines.append(ru.STATS_TOP_POSTS_TITLE)
    if not top:
        lines.append(ru.STATS_TOP_POSTS_EMPTY)
    for i, (message_id, total, day) in enumerate(top, start=1):
        lines.append(
            ru.STATS_TOP_POST_ROW.format(
                n=i,
                total=total,
                day=day.strftime("%d.%m"),
                link=channel_stats.post_link(chat, message_id),
            )
        )
    return Screen(
        "\n".join(lines),
        rows=_tab_rows(target, "posts", back, CHANNEL_TABS),
        has_back_row=back is not None,
    )


async def stats_screen(
    tab: str,
    bot: Bot,
    session: AsyncSession,
    chat: Chat,
    *,
    target: TabTarget,
    back: Btn | None,
) -> Screen:
    if chat.is_channel:
        if tab == "dynamics":
            return await channel_dynamics_screen(session, chat, target=target, back=back)
        if tab == "posts":
            return await channel_posts_screen(session, chat, target=target, back=back)
        if tab == "hours":
            screen = await hours_screen(session, chat, target=target, back=back)
            return Screen(
                screen.text,
                rows=_tab_rows(target, "hours", back, CHANNEL_TABS),
                has_back_row=back is not None,
            )
        return await channel_overview_screen(bot, session, chat, target=target, back=back)
    if tab == "users":
        return await top_users_screen(session, chat, target=target, back=back)
    if tab == "words":
        return await top_words_screen(session, chat, target=target, back=back)
    if tab == "hours":
        return await hours_screen(session, chat, target=target, back=back)
    return await overview_screen(bot, session, chat, target=target, back=back)


async def me_screen(session: AsyncSession, chat: Chat, user_tg_id: int) -> Screen:
    today = local_today(chat.timezone)
    data = await stats_service.user_stats(session, chat.telegram_id, user_tg_id, today)
    rank_line = (
        ru.ME_RANK_LINE.format(rank=data.rank_week, active=data.active_week)
        if data.rank_week
        else ""
    )
    text = ru.ME_BODY.format(
        title=chat.title or chat.telegram_id,
        today=data.today,
        week=data.week,
        month=data.month,
        rank_line=rank_line,
    )
    return Screen(text)
