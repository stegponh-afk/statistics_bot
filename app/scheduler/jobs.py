import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.cache import Cache
from app.database.models import BotStatus, Chat
from app.database.session import async_session_factory
from app.services import chat_service, stats_service
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


async def job_purge_stats() -> None:
    async with async_session_factory() as session:
        events, words = await stats_service.purge_older_than(session, settings.stats_retention_days)
    logger.info("purged %d events and %d word rows", events, words)


def setup_scheduler(bot: Bot, cache: Cache) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        job_resync_admins, CronTrigger(hour=4, minute=30), args=[bot, cache], id="resync_admins"
    )
    scheduler.add_job(job_purge_stats, CronTrigger(hour=4, minute=0), id="purge_stats")
    scheduler.start()
    return scheduler
