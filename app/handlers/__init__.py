"""Three top-level routers, one per chat kind. Group-side middlewares (the
force-sub gate, message logging) hang off group_router so they run for
every group message whether or not a handler matches."""

from aiogram import Router

from app.cache import Cache
from app.filters.chat_type import CB_GROUP, CB_PRIVATE, CHANNEL, GROUP, PRIVATE
from app.handlers.channel import membership as channel_membership
from app.handlers.group import commands as group_commands
from app.handlers.group import membership as group_membership
from app.handlers.private import help as private_help
from app.handlers.private import my_chats, settings, start


def build_router(cache: Cache) -> Router:
    root = Router(name="root")

    private_router = Router(name="private")
    private_router.message.filter(PRIVATE)
    private_router.callback_query.filter(CB_PRIVATE)
    private_router.include_router(start.router)
    private_router.include_router(my_chats.router)
    private_router.include_router(settings.router)
    private_router.include_router(private_help.router)

    group_router = Router(name="group")
    group_router.message.filter(GROUP)
    group_router.callback_query.filter(CB_GROUP)
    group_router.include_router(group_membership.router)
    group_router.include_router(group_commands.router)

    channel_router = Router(name="channel")
    channel_router.channel_post.filter(CHANNEL)
    channel_router.include_router(channel_membership.router)

    root.include_router(private_router)
    root.include_router(group_router)
    root.include_router(channel_router)
    return root
