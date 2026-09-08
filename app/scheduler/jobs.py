import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.cache import Cache
from app.database.models import BotStatus, Chat
from app.database.session import async_session_factory
from app.services import broadcast_delivery, broadcast_service, chat_service, stats_service
from config import settings

logger = logging.getLogger(__name__)


async def job_resync_admins(bot: Bot, cache: Cache) -> None:
    async with async_session_factory() as session:
        chats = list(
            await session.scalars(select(Chat).where(Chat.bot_status == BotStatus.ADMINISTRATOR))
        )
        for chat in chats:
            try:
                await chat_service.sync_admins(bot, session, chat, cache)
            except Exception:  # noqa: BLE001 — one bad chat must not stop the sweep
                logger.exception("resync admins failed for %s", chat.telegram_id)
    logger.info("resynced admins for %d chats", len(chats))


async def job_snapshot_members(bot: Bot) -> None:
    """Hourly: refresh subscriber counts so the per-day history has a
    value even for chats nobody opened today."""
    async with async_session_factory() as session:
        chats = list(
            await session.scalars(
                select(Chat)
                .where(Chat.bot_status.in_([BotStatus.MEMBER, BotStatus.ADMINISTRATOR]))
                .limit(500)
            )
        )
        for chat in chats:
            chat.member_count_updated_at = None
            try:
                await chat_service.get_member_count(bot, session, chat)
            except Exception:  # noqa: BLE001
                logger.exception("member snapshot failed for %s", chat.telegram_id)


async def job_purge_stats() -> None:
    async with async_session_factory() as session:
        events, words = await stats_service.purge_older_than(session, settings.stats_retention_days)
    logger.info("purged %d events and %d word rows", events, words)


async def job_run_due_broadcasts(bot: Bot) -> None:
    async with async_session_factory() as session:
        due = await broadcast_service.due_broadcasts(session)
        for broadcast in due:
            try:
                await broadcast_delivery.run_broadcast(session, bot, broadcast)
            except Exception:  # noqa: BLE001 — one broken broadcast must not block the rest
                logger.exception("broadcast %s failed", broadcast.id)
                broadcast_service.advance_after_run(broadcast)
                await session.commit()


def setup_scheduler(bot: Bot, cache: Cache) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        job_resync_admins, CronTrigger(hour=4, minute=30), args=[bot, cache], id="resync_admins"
    )
    scheduler.add_job(job_purge_stats, CronTrigger(hour=4, minute=0), id="purge_stats")
    scheduler.add_job(
        job_snapshot_members, CronTrigger(minute=50), args=[bot], id="snapshot_members"
    )
    scheduler.add_job(
        job_run_due_broadcasts,
        IntervalTrigger(seconds=30),
        args=[bot],
        id="run_broadcasts",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    return scheduler
