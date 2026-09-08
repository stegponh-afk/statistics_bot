from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from config import settings


def get_zone(name: str | None) -> ZoneInfo:
    for candidate in (name, settings.default_timezone, "UTC"):
        if not candidate:
            continue
        try:
            return ZoneInfo(candidate)
        except ZoneInfoNotFoundError:
            continue
    return ZoneInfo("UTC")


def ensure_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def localize(dt: datetime, tz_name: str | None) -> tuple[date, int]:
    """(local calendar day, local hour 0..23) of a UTC/aware datetime in the
    given IANA zone — what message_events.local_day/local_hour store."""
    local = ensure_aware(dt).astimezone(get_zone(tz_name))
    return local.date(), local.hour


def local_today(tz_name: str | None, now: datetime | None = None) -> date:
    return localize(now or datetime.now(UTC), tz_name)[0]


def pluralize(n: int, one: str, few: str, many: str) -> str:
    """Russian plural form for n: pluralize(5, "сообщение", "сообщения", "сообщений")."""
    n = abs(n) % 100
    if 11 <= n <= 19:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


def format_count(n: int, one: str, few: str, many: str) -> str:
    return f"{n} {pluralize(n, one, few, many)}"


def display_name(full_name: str | None, username: str | None, telegram_id: int) -> str:
    if full_name:
        return full_name
    if username:
        return f"@{username}"
    return f"id:{telegram_id}"
