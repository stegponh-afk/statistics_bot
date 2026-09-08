"""Three top-level routers, one per chat kind. Group-side middlewares (the
force-sub gate, message logging) hang off group_router so they run for
every group message whether or not a handler matches."""

from aiogram import Router

from app.cache import Cache
from app.filters.chat_type import CB_GROUP, CB_PRIVATE, CHANNEL, GROUP, PRIVATE
from app.handlers import join_requests
from app.handlers.channel import membership as channel_membership
from app.handlers.group import auto_forward as group_auto_forward
from app.handlers.group import commands as group_commands
from app.handlers.group import gate_callbacks as group_gate
from app.handlers.group import membership as group_membership
from app.handlers.group import stats_callbacks as group_stats
from app.handlers.group import welcome as group_welcome
from app.handlers.private import (
    admin,
    bots,
    broadcast,
    channel_check,
    channels_binding,
    chat_panel,
    digest,
    join_check,
    my_chats,
    reward,
    settings,
    start,
    subscribe,
    welcome,
    whitelist,
)
from app.handlers.private import help as private_help
from app.middlewares.gate import ForceSubGateMiddleware
from app.middlewares.stats_log import StatsLogMiddleware


def build_router(cache: Cache) -> Router:
    root = Router(name="root")

    private_router = Router(name="private")
    private_router.message.filter(PRIVATE)
    private_router.callback_query.filter(CB_PRIVATE)
    private_router.include_router(subscribe.router)
    private_router.include_router(start.router)
    private_router.include_router(my_chats.router)
    private_router.include_router(chat_panel.router)
    private_router.include_router(channels_binding.router)
    private_router.include_router(channel_check.router)
    private_router.include_router(join_check.router)
    private_router.include_router(reward.router)
    private_router.include_router(welcome.router)
    private_router.include_router(digest.router)
    private_router.include_router(whitelist.router)
    private_router.include_router(bots.router)
    private_router.include_router(broadcast.router)
    private_router.include_router(admin.router)
    private_router.include_router(settings.router)
    private_router.include_router(private_help.router)

    group_router = Router(name="group")
    group_router.message.filter(GROUP)
    group_router.callback_query.filter(CB_GROUP)
    # Outer middlewares run before any handler filter, for every message
    # that reaches this router — first registered runs first, so the gate
    # can swallow a message before it is ever logged.
    group_router.message.outer_middleware(ForceSubGateMiddleware(cache))
    group_router.message.outer_middleware(StatsLogMiddleware())
    group_router.include_router(group_auto_forward.router)
    group_router.include_router(group_membership.router)
    group_router.include_router(group_commands.router)
    group_router.include_router(group_stats.router)
    group_router.include_router(group_gate.router)
    group_router.include_router(group_welcome.router)

    channel_router = Router(name="channel")
    channel_router.channel_post.filter(CHANNEL)
    channel_router.channel_post.outer_middleware(StatsLogMiddleware())
    channel_router.include_router(channel_membership.router)

    # chat_join_request arrives for groups and channels alike, so it is
    # handled above the per-chat-kind routers.
    root.include_router(join_requests.router)
    root.include_router(private_router)
    root.include_router(group_router)
    root.include_router(channel_router)
    return root
