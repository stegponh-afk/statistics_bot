"""«Рассылка»: compose a message, pick chats, send now / at a time /
on a weekly schedule; list and manage existing broadcasts.

  bc:menu | bc:cancel      leave the wizard (the draft is kept) -> the section
  bc:new                   start composing (FSM)   bc:new:fresh  drop the draft first
  bc:draft | bc:draft:del  resume / delete the saved draft
  bc:t:c:{chat_id}         toggle a chat target      bc:t:b:{key_id}  toggle a bot
  bc:t:next                targets chosen -> ask for the message
  bc:b:{step}              one step back
  bc:nobtn                 skip buttons -> preview
  bc:now | bc:at | bc:rec  choose when
  bc:d:{0..6} | bc:d:all | bc:d:next   weekday toggles for recurring
  bc:list                  my broadcasts
  bc:autodel | bc:autodelr auto-delete by time / by reactions
  bc:{id}                  one broadcast; :preview :pause :resume :run :del
                           :edit rewrite the published post
                           :delposts take it down everywhere
"""

from dataclasses import replace

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.database.models import (
    Broadcast,
    BroadcastDraft,
    BroadcastKind,
    BroadcastStatus,
    Chat,
    User,
)
from app.services import broadcast_delivery, broadcast_service, chat_service, post_service
from app.services.broadcast_service import (
    WEEKDAY_LABELS,
    Content,
    content_from_message,
    format_days,
    format_duration,
    format_local,
    parse_buttons,
    parse_datetime,
    parse_duration,
    parse_time,
)
from app.services.chat_service import list_admin_chats
from app.texts import ru
from app.ui import Btn, Screen, respond, send
from app.ui.blocks import strip_tags
from app.ui.buttons import STYLE_DANGER, STYLE_PRIMARY, STYLE_SUCCESS
from app.utils import pluralize
from config import settings

router = Router(name="broadcast")


class BroadcastNew(StatesGroup):
    targets = State()
    message = State()
    buttons = State()
    schedule = State()
    ad_label = State()
    autodelete = State()
    autodelete_reactions = State()
    datetime = State()
    days = State()
    time = State()


def _rich(user: User | None) -> bool:
    return user.rich_buttons_enabled if user else True


def _tz() -> str:
    return settings.default_timezone


# --- screens --------------------------------------------------------------


def _draft_snippet(draft: BroadcastDraft) -> str:
    content = draft.data.get("content")
    return _snippet(Content.from_json(content)) if content else ru.BROADCAST_DRAFT_NO_TEXT


async def _draft(session: AsyncSession, user: User | None) -> BroadcastDraft | None:
    return await broadcast_service.load_draft(session, user) if user else None


async def menu_screen(session: AsyncSession, user: User | None) -> Screen:
    draft = await _draft(session, user)
    line = (
        ru.BROADCAST_DRAFT_LINE.format(
            when=format_local(draft.updated_at, _tz()), snippet=_draft_snippet(draft)
        )
        if draft
        else ""
    )
    rows = [[Btn(ru.BTN_BROADCAST_NEW, "bc:new"), Btn(ru.BTN_BROADCAST_LIST, "bc:list")]]
    if draft:
        rows.insert(0, [Btn(ru.BTN_DRAFT_CONTINUE, "bc:draft", STYLE_PRIMARY)])
        rows.append([Btn(ru.BTN_DRAFT_DELETE, "bc:draft:del", STYLE_DANGER)])
    rows.append([Btn(ru.BTN_BACK, "menu:main")])
    return Screen(ru.BROADCAST_MENU.format(draft=line), rows=rows)


async def _available_targets(session: AsyncSession, user: User) -> list[Chat]:
    return [c for c in await list_admin_chats(session, user) if c.is_active]


async def targets_screen(session: AsyncSession, user: User, chosen_chats: set[int]) -> Screen:
    chats = await _available_targets(session, user)
    rows: list[list[Btn]] = []
    for chat in chats:
        icon = "📣" if chat.is_channel else "👥"
        title = f"{icon} {chat.title or chat.telegram_id}"
        label = (
            ru.BROADCAST_TARGET_ON if chat.id in chosen_chats else ru.BROADCAST_TARGET_OFF
        ).format(title=title)
        rows.append([Btn(label, f"bc:t:c:{chat.id}")])
    rows.append([Btn(ru.BTN_NEXT, "bc:t:next", STYLE_PRIMARY)])
    rows.append(_leave_row())
    return Screen(ru.BROADCAST_PICK_TARGETS.format(count=len(chosen_chats)), rows=rows)


def _leave_row(back_to: str | None = None) -> list[Btn]:
    """Every step of the wizard can be stepped back from, and leaving it
    keeps the draft — so nothing an admin typed is ever one tap from gone."""
    row = [Btn(ru.BTN_WIZARD_EXIT, "bc:cancel", STYLE_DANGER)]
    if back_to:
        row.insert(0, Btn(ru.BTN_BACK, f"bc:b:{back_to}"))
    return row


def message_screen() -> Screen:
    return Screen(ru.BROADCAST_ASK_MESSAGE, rows=[_leave_row("targets")])


def buttons_screen() -> Screen:
    return Screen(
        ru.BROADCAST_ASK_BUTTONS,
        rows=[[Btn(ru.BTN_NO_BUTTONS, "bc:nobtn")], _leave_row("message")],
    )


def days_screen(chosen: set[int]) -> Screen:
    day_buttons = [
        Btn(("✅ " if d in chosen else "") + WEEKDAY_LABELS[d], f"bc:d:{d}") for d in range(7)
    ]
    rows = [day_buttons[:4], day_buttons[4:], [Btn(ru.BTN_EVERY_DAY, "bc:d:all")]]
    rows.append([Btn(ru.BTN_NEXT, "bc:d:next", STYLE_PRIMARY)])
    rows.append(_leave_row("schedule"))
    label = format_days(sorted(chosen)) if chosen else "—"
    return Screen(ru.BROADCAST_PICK_DAYS.format(days=label), rows=rows)


def _kind_label(kind: str) -> str:
    return {
        BroadcastKind.NOW.value: ru.BROADCAST_KIND_NOW,
        BroadcastKind.ONCE.value: ru.BROADCAST_KIND_ONCE,
        BroadcastKind.RECURRING.value: ru.BROADCAST_KIND_RECURRING,
    }.get(kind, kind)


def _snippet(content: Content) -> str:
    text = strip_tags(content.text or "")
    if not text:
        return f"[{content.type}]"
    return text if len(text) <= 80 else text[:77] + "…"


async def list_screen(session: AsyncSession, user: User) -> Screen:
    items = await broadcast_service.list_broadcasts(session, user)
    text = ru.BROADCASTS_TITLE
    if not items:
        text += f"\n{ru.SEPARATOR}\n{ru.BROADCASTS_EMPTY_LINE}"
    rows = []
    for b in items[:30]:
        icon = ru.BROADCAST_STATUS.get(b.status, "").split(" ")[0]
        title = f"#{b.id} · {_kind_label(b.kind)} · {_snippet(Content.from_json(b.content))}"
        rows.append([Btn(ru.BROADCAST_ROW.format(icon=icon, title=title)[:60], f"bc:{b.id}")])
    rows.append([Btn(ru.BTN_BACK, "bc:menu")])
    return Screen(text, rows=rows)


async def card_screen(session: AsyncSession, b: Broadcast) -> Screen:
    chats = await broadcast_service.targets(session, b)
    target_names = [c.title or str(c.telegram_id) for c in chats]
    if b.kind == BroadcastKind.ONCE.value:
        schedule_line = ru.BROADCAST_SCHEDULE_ONCE.format(
            when=format_local(b.scheduled_at, b.timezone), tz=b.timezone
        )
    elif b.kind == BroadcastKind.RECURRING.value:
        schedule_line = ru.BROADCAST_SCHEDULE_RECURRING.format(
            days=format_days(b.recur_days_list),
            time=b.recur_time,
            tz=b.timezone,
            next=format_local(b.next_run_at, b.timezone),
        )
    else:
        schedule_line = ""
    text = ru.BROADCAST_CARD.format(
        id=b.id,
        kind=_kind_label(b.kind),
        status=ru.BROADCAST_STATUS.get(b.status, b.status),
        targets=", ".join(target_names) or "—",
        schedule_line=schedule_line,
        runs=b.runs_count,
        sent=b.sent_count,
        failed=b.failed_count,
        last_run=format_local(b.last_run_at, b.timezone),
        snippet=_snippet(Content.from_json(b.content)),
    )
    posts = await post_service.stats(session, b.id)
    if posts.published or posts.deleted:
        text += ru.BROADCAST_CARD_POSTS.format(
            published=posts.published, deleted=posts.deleted, reactions=posts.reactions
        )
    rows = [[Btn(ru.BTN_BROADCAST_PREVIEW, f"bc:{b.id}:preview")]]
    # Only a post that is still standing can be rewritten or taken down.
    if posts.published:
        rows.append(
            [
                Btn(ru.BTN_POST_EDIT, f"bc:{b.id}:edit"),
                Btn(ru.BTN_POST_DELETE, f"bc:{b.id}:delposts", STYLE_DANGER),
            ]
        )
    if b.status == BroadcastStatus.SCHEDULED.value and b.kind != BroadcastKind.NOW.value:
        rows.append([Btn(ru.BTN_BROADCAST_PAUSE, f"bc:{b.id}:pause")])
    elif b.status == BroadcastStatus.PAUSED.value:
        rows.append([Btn(ru.BTN_BROADCAST_RESUME, f"bc:{b.id}:resume", STYLE_SUCCESS)])
    rows.append(
        [
            Btn(ru.BTN_BROADCAST_RUN_NOW, f"bc:{b.id}:run"),
            Btn(ru.BTN_BROADCAST_DELETE, f"bc:{b.id}:del", STYLE_DANGER),
        ]
    )
    rows.append([Btn(ru.BTN_BACK, "bc:list")])
    return Screen(text, rows=rows)


# --- entry ------------------------------------------------------------------


@router.message(Command("broadcast"))
async def cmd_broadcast(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    await _keep_draft(session, user, state)
    await send(
        message.bot, message.chat.id, await menu_screen(session, user), rich_buttons=_rich(user)
    )


# Which state to come back to. The steps that only ask for a date or a
# weekday are transient: the draft returns to the preview instead.
STEPS = {
    "targets": BroadcastNew.targets,
    "message": BroadcastNew.message,
    "buttons": BroadcastNew.buttons,
    "schedule": BroadcastNew.schedule,
}


def _step_of(state_name: str | None) -> str:
    step = (state_name or "").split(":")[-1]
    return step if step in STEPS else "schedule"


async def _remember(session: AsyncSession, user: User, step: str, data: dict) -> None:
    """Stores the draft, or removes it once nothing is left to remember."""
    if data.get("content") or data.get("chats"):
        await broadcast_service.save_draft(session, user, step, data)
    else:
        await broadcast_service.drop_draft(session, user)


async def _keep_draft(session: AsyncSession, user: User, state: FSMContext) -> bool:
    """Saves what has been composed so far and leaves the wizard. Returns
    whether there was anything worth keeping."""
    data = await state.get_data()
    keep = bool(data.get("content") or data.get("chats"))
    if keep:
        await broadcast_service.save_draft(session, user, _step_of(await state.get_state()), data)
    await state.clear()
    return keep


@router.callback_query(F.data.in_({"bc:menu", "bc:cancel"}))
async def cb_menu(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    saved = await _keep_draft(session, user, state)
    await callback.answer(ru.BROADCAST_DRAFT_SAVED if saved else "")
    await respond(callback, await menu_screen(session, user), rich_buttons=_rich(user))


@router.callback_query(F.data.in_({"bc:new", "bc:new:fresh"}))
async def cb_new(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    if not await _available_targets(session, user):
        await respond(
            callback,
            Screen(ru.BROADCAST_NO_TARGETS, rows=[[Btn(ru.BTN_BACK, "bc:menu")]]),
            rich_buttons=_rich(user),
        )
        return
    draft = await _draft(session, user)
    if draft is not None and callback.data == "bc:new":
        # Starting over would overwrite the draft, so say so first.
        screen = Screen(
            ru.BROADCAST_DRAFT_EXISTS.format(
                when=format_local(draft.updated_at, _tz()), snippet=_draft_snippet(draft)
            ),
            rows=[
                [Btn(ru.BTN_DRAFT_CONTINUE, "bc:draft", STYLE_PRIMARY)],
                [Btn(ru.BTN_DRAFT_FRESH, "bc:new:fresh", STYLE_DANGER)],
                [Btn(ru.BTN_BACK, "bc:menu")],
            ],
        )
        await respond(callback, screen, rich_buttons=_rich(user))
        return
    await broadcast_service.drop_draft(session, user)
    await state.set_state(BroadcastNew.targets)
    await state.set_data({"chats": []})
    await respond(callback, await targets_screen(session, user, set()), rich_buttons=_rich(user))


@router.callback_query(F.data == "bc:draft")
async def cb_draft_resume(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    draft = await _draft(session, user)
    if draft is None:
        await callback.answer(ru.BROADCAST_DRAFT_GONE, show_alert=True)
        await respond(callback, await menu_screen(session, user), rich_buttons=_rich(user))
        return
    step = draft.step if draft.step in STEPS else "schedule"
    await state.set_data(dict(draft.data))
    await state.set_state(STEPS[step])
    await callback.answer()
    if step == "schedule":
        # The composed post is shown again above the preview: after a day
        # away nobody remembers what exactly they had written.
        await _show_preview(callback.message.chat.id, callback.bot, session, user, state)
        return
    await _show_step(callback, session, user, state, step)


@router.callback_query(F.data == "bc:draft:del")
async def cb_draft_delete(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    await state.clear()
    await broadcast_service.drop_draft(session, user)
    await callback.answer(ru.BROADCAST_DRAFT_DROPPED)
    await respond(callback, await menu_screen(session, user), rich_buttons=_rich(user))


async def _show_step(
    callback: CallbackQuery, session: AsyncSession, user: User, state: FSMContext, step: str
) -> None:
    """Renders one step of the wizard in place (used by «Назад» and by
    resuming a draft)."""
    data = await state.get_data()
    await state.set_state(STEPS[step])
    if step == "targets":
        screen = await targets_screen(session, user, set(data.get("chats", [])))
    elif step == "message":
        screen = message_screen()
    elif step == "buttons":
        screen = buttons_screen()
    else:
        screen = await preview_screen(
            callback.bot,
            session,
            user,
            data,
            has_channels=await _has_channel_target(session, list(data.get("chats", []))),
        )
    await respond(callback, screen, rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^bc:b:(\w+)$"))
async def cb_back(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    step = callback.data.rsplit(":", 1)[1]
    data = await state.get_data()
    if step == "days":
        await state.set_state(BroadcastNew.days)
        await respond(callback, days_screen(set(data.get("days", []))), rich_buttons=_rich(user))
        return
    if step not in STEPS or (step != "targets" and "content" not in data):
        # Nothing to go back to (a stale screen after a restart).
        await callback.answer()
        await respond(callback, await menu_screen(session, user), rich_buttons=_rich(user))
        return
    await callback.answer()
    await _show_step(callback, session, user, state, step)


@router.callback_query(BroadcastNew.targets, F.data.regexp(r"^bc:t:c:(\d+)$"))
async def cb_toggle_target(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    target_id = int(callback.data.rsplit(":", 1)[1])
    data = await state.get_data()
    chosen = set(data.get("chats", []))
    chosen.symmetric_difference_update({target_id})
    data["chats"] = sorted(chosen)
    await state.set_data(data)
    # Saved on every tap, not only when the step is finished: another
    # section can take over the FSM at any moment.
    await _remember(session, user, "targets", data)
    await respond(
        callback, await targets_screen(session, user, set(data["chats"])), rich_buttons=_rich(user)
    )


@router.callback_query(BroadcastNew.targets, F.data == "bc:t:next")
async def cb_targets_next(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    data = await state.get_data()
    if not data.get("chats"):
        await callback.answer(ru.BROADCAST_NEED_TARGET, show_alert=True)
        return
    await state.set_state(BroadcastNew.message)
    await _remember(session, user, "message", data)
    await respond(callback, message_screen(), rich_buttons=_rich(user))


@router.message(BroadcastNew.message)
async def on_message_content(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    content = content_from_message(message)
    if content is None:
        await send(
            message.bot, message.chat.id, Screen(ru.BROADCAST_UNSUPPORTED), rich_buttons=_rich(user)
        )
        return
    data = await state.update_data(content=content.to_json())
    await state.set_state(BroadcastNew.buttons)
    await _remember(session, user, "buttons", data)
    await send(message.bot, message.chat.id, buttons_screen(), rich_buttons=_rich(user))


async def _comments_note(bot, session: AsyncSession, chat_ids: list[int]) -> str:
    """Comments under a channel post belong to the channel, not to the post:
    they appear when a discussion group is attached and cannot be switched
    per message. So the preview says what will happen and how to change it,
    instead of offering a switch that does not exist."""
    if not chat_ids:
        return ""
    channels = [
        c for c in await session.scalars(select(Chat).where(Chat.id.in_(chat_ids))) if c.is_channel
    ]
    if not channels:
        return ""
    with_comments: list[str] = []
    without: list[str] = []
    for channel in channels:
        await chat_service.refresh_chat_flags(bot, session, channel)
        title = channel.title or str(channel.telegram_id)
        (with_comments if channel.linked_chat_tg_id else without).append(title)
    note = ""
    if with_comments:
        note += ru.BROADCAST_COMMENTS_ON.format(titles=", ".join(with_comments))
    if without:
        note += ru.BROADCAST_COMMENTS_OFF.format(titles=", ".join(without))
    return note


# Per-post switches on the preview screen: FSM key -> (label off, label on).
OPTIONS = {
    "silent": (ru.BTN_OPT_SOUND_ON, ru.BTN_OPT_SOUND_OFF),
    "pin": (ru.BTN_OPT_PIN_OFF, ru.BTN_OPT_PIN_ON),
    "protect": (ru.BTN_OPT_PROTECT_OFF, ru.BTN_OPT_PROTECT_ON),
    "comments": (ru.BTN_OPT_COMMENTS_OFF, ru.BTN_OPT_COMMENTS_ON),
    "is_ad": (ru.BTN_OPT_AD_OFF, ru.BTN_OPT_AD_ON),
}


def _option_button(content: Content, name: str) -> Btn:
    off, on = OPTIONS[name]
    return Btn(on if getattr(content, name) else off, f"bc:o:{name}")


# Auto-delete presets, in minutes, and the reaction counts offered as
# ready-made answers next to «своё число».
AUTODELETE_PRESETS = (60, 6 * 60, 24 * 60, 3 * 24 * 60, 7 * 24 * 60)
REACTION_PRESETS = (50, 100, 500, 1000)
MAX_REACTION_TRIGGER = 1_000_000


def _autodelete_buttons(content: Content) -> list[Btn]:
    minutes, count = content.autodelete_after, content.autodelete_reactions
    return [
        Btn(
            ru.BTN_OPT_AUTODELETE_ON.format(when=format_duration(minutes))
            if minutes
            else ru.BTN_OPT_AUTODELETE_OFF,
            "bc:autodel",
        ),
        Btn(
            ru.BTN_OPT_AUTODELETE_R_ON.format(count=count)
            if count
            else ru.BTN_OPT_AUTODELETE_R_OFF,
            "bc:autodelr",
        ),
    ]


def _autodelete_note(content: Content) -> str:
    """Two triggers, whichever comes first — said in those words, because
    «удалится через час ИЛИ на 100 реакциях» is not obvious."""
    conditions = []
    if content.autodelete_after:
        conditions.append(
            ru.BROADCAST_AUTODELETE_BY_TIME.format(when=format_duration(content.autodelete_after))
        )
    if content.autodelete_reactions:
        conditions.append(
            ru.BROADCAST_AUTODELETE_BY_REACTIONS.format(
                count=f"{content.autodelete_reactions} "
                + pluralize(content.autodelete_reactions, "реакцию", "реакции", "реакций")
            )
        )
    if not conditions:
        return ""
    return ru.BROADCAST_AUTODELETE_NOTE.format(
        conditions=ru.BROADCAST_AUTODELETE_JOINER.join(conditions)
    )


def autodelete_screen(content: Content) -> Screen:
    rows = [
        [Btn(format_duration(m), f"bc:autodel:{m}") for m in AUTODELETE_PRESETS[:3]],
        [Btn(format_duration(m), f"bc:autodel:{m}") for m in AUTODELETE_PRESETS[3:]],
        [Btn(ru.BTN_AUTODELETE_OFF, "bc:autodel:off")],
        _leave_row("schedule"),
    ]
    current = format_duration(content.autodelete_after)
    return Screen(ru.BROADCAST_ASK_AUTODELETE.format(current=current), rows=rows)


def autodelete_reactions_screen(content: Content) -> Screen:
    rows = [
        [Btn(str(n), f"bc:autodelr:{n}") for n in REACTION_PRESETS],
        [Btn(ru.BTN_AUTODELETE_OFF, "bc:autodelr:off")],
        _leave_row("schedule"),
    ]
    current = str(content.autodelete_reactions or "—")
    return Screen(ru.BROADCAST_ASK_AUTODELETE_REACTIONS.format(current=current), rows=rows)


async def preview_screen(
    bot, session: AsyncSession, user: User, data: dict, *, has_channels: bool
) -> Screen:
    content = Content.from_json(data["content"])
    chat_ids = list(data.get("chats", []))
    # Everything the admin should know before choosing the time, said
    # above the question rather than after it.
    notes = ""
    if content.is_ad:
        notes += ru.BROADCAST_AD_NOTE.format(label=broadcast_delivery.ad_label_of(user))
    notes += _autodelete_note(content)
    text = ru.BROADCAST_PREVIEW_HINT.format(
        targets=len(chat_ids),
        comments=await _comments_note(bot, session, chat_ids),
        notes=notes,
    )
    rows = [
        [_option_button(content, "silent"), _option_button(content, "pin")],
        [_option_button(content, "protect"), _option_button(content, "is_ad")],
        _autodelete_buttons(content),
    ]
    # A channel post gets comments from its discussion group; in a group
    # the switch would mean nothing, so it is only offered when it can act.
    if has_channels:
        rows.append([_option_button(content, "comments")])
    if content.is_ad:
        rows.append([Btn(ru.BTN_AD_LABEL_EDIT, "bc:adlabel")])
    rows += [
        [Btn(ru.BTN_SEND_NOW, "bc:now", STYLE_SUCCESS)],
        [Btn(ru.BTN_SEND_AT, "bc:at")],
        [Btn(ru.BTN_SEND_RECURRING, "bc:rec")],
        _leave_row("buttons"),
    ]
    return Screen(text, rows=rows)


async def _has_channel_target(session: AsyncSession, chat_ids: list[int]) -> bool:
    if not chat_ids:
        return False
    return any(
        c.is_channel for c in await session.scalars(select(Chat).where(Chat.id.in_(chat_ids)))
    )


async def _show_preview(
    chat_id: int, bot, session: AsyncSession, user: User, state: FSMContext
) -> None:
    data = await state.get_data()
    content = Content.from_json(data["content"])
    await broadcast_delivery.send_content(bot, chat_id, content, content.file_id)
    screen = await preview_screen(
        bot,
        session,
        user,
        data,
        has_channels=await _has_channel_target(session, list(data.get("chats", []))),
    )
    await state.set_state(BroadcastNew.schedule)
    await _remember(session, user, "schedule", data)
    await send(bot, chat_id, screen, rich_buttons=_rich(user))


@router.callback_query(BroadcastNew.schedule, F.data.regexp(r"^bc:o:(\w+)$"))
async def cb_toggle_option(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    name = callback.data.rsplit(":", 1)[1]
    if name not in OPTIONS:
        await callback.answer()
        return
    data = await state.get_data()
    data["content"][name] = not data["content"].get(name, name == "comments")
    await state.set_data(data)
    await _remember(session, user, "schedule", data)
    screen = await preview_screen(
        callback.bot,
        session,
        user,
        data,
        has_channels=await _has_channel_target(session, list(data.get("chats", []))),
    )
    await respond(callback, screen, rich_buttons=_rich(user))


async def _content_of(state: FSMContext) -> Content:
    return Content.from_json((await state.get_data())["content"])


async def _set_content_option(
    session: AsyncSession, user: User, state: FSMContext, name: str, value: object
) -> dict:
    data = await state.get_data()
    data["content"][name] = value
    await state.set_data(data)
    await state.set_state(BroadcastNew.schedule)
    await _remember(session, user, "schedule", data)
    return data


async def _preview_again(
    bot, session: AsyncSession, user: User, data: dict, callback: CallbackQuery | None, chat_id: int
) -> None:
    screen = await preview_screen(
        bot,
        session,
        user,
        data,
        has_channels=await _has_channel_target(session, list(data.get("chats", []))),
    )
    if callback is not None:
        await respond(callback, screen, rich_buttons=_rich(user))
    else:
        await send(bot, chat_id, screen, rich_buttons=_rich(user))


@router.callback_query(BroadcastNew.schedule, F.data.in_({"bc:autodel", "bc:autodelr"}))
async def cb_autodelete_open(callback: CallbackQuery, user: User | None, state: FSMContext) -> None:
    if user is None:
        await callback.answer()
        return
    content = await _content_of(state)
    by_time = callback.data == "bc:autodel"
    await state.set_state(BroadcastNew.autodelete if by_time else BroadcastNew.autodelete_reactions)
    screen = autodelete_screen(content) if by_time else autodelete_reactions_screen(content)
    await respond(callback, screen, rich_buttons=_rich(user))


@router.callback_query(BroadcastNew.autodelete, F.data.regexp(r"^bc:autodel:(\d+|off)$"))
async def cb_autodelete_pick(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    raw = callback.data.rsplit(":", 1)[1]
    minutes = None if raw == "off" else int(raw)
    data = await _set_content_option(session, user, state, "autodelete_after", minutes)
    await callback.answer(
        ru.BROADCAST_AUTODELETE_SET.format(when=format_duration(minutes))
        if minutes
        else ru.BROADCAST_AUTODELETE_CLEARED
    )
    await _preview_again(callback.bot, session, user, data, callback, callback.message.chat.id)


@router.message(BroadcastNew.autodelete, F.text)
async def on_autodelete_text(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    minutes = parse_duration(message.text)
    if minutes is None:
        await send(
            message.bot,
            message.chat.id,
            Screen(ru.BROADCAST_BAD_DURATION),
            rich_buttons=_rich(user),
        )
        return
    data = await _set_content_option(session, user, state, "autodelete_after", minutes)
    await _preview_again(message.bot, session, user, data, None, message.chat.id)


@router.callback_query(BroadcastNew.autodelete_reactions, F.data.regexp(r"^bc:autodelr:(\d+|off)$"))
async def cb_autodelete_reactions_pick(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    raw = callback.data.rsplit(":", 1)[1]
    count = None if raw == "off" else int(raw)
    data = await _set_content_option(session, user, state, "autodelete_reactions", count)
    await callback.answer(
        ru.BROADCAST_AUTODELETE_R_SET.format(count=count)
        if count
        else ru.BROADCAST_AUTODELETE_CLEARED
    )
    await _preview_again(callback.bot, session, user, data, callback, callback.message.chat.id)


@router.message(BroadcastNew.autodelete_reactions, F.text)
async def on_autodelete_reactions_text(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    raw = message.text.strip().replace(" ", "")
    if not raw.isdigit() or not 0 < int(raw) <= MAX_REACTION_TRIGGER:
        await send(
            message.bot, message.chat.id, Screen(ru.BROADCAST_BAD_COUNT), rich_buttons=_rich(user)
        )
        return
    data = await _set_content_option(session, user, state, "autodelete_reactions", int(raw))
    await _preview_again(message.bot, session, user, data, None, message.chat.id)


@router.callback_query(BroadcastNew.schedule, F.data == "bc:adlabel")
async def cb_ad_label(callback: CallbackQuery, user: User | None, state: FSMContext) -> None:
    if user is None:
        await callback.answer()
        return
    await state.set_state(BroadcastNew.ad_label)
    screen = Screen(
        ru.BROADCAST_ASK_AD_LABEL.format(
            current=broadcast_delivery.ad_label_of(user),
            default=broadcast_delivery.DEFAULT_AD_LABEL,
        ),
        rows=[_leave_row("schedule")],
    )
    await respond(callback, screen, rich_buttons=_rich(user))


@router.message(BroadcastNew.ad_label, F.text)
async def on_ad_label(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    label = message.text.strip()
    if len(label) > 64:
        await message.answer(ru.BROADCAST_AD_LABEL_TOO_LONG)
        return
    user.ad_label = label
    await session.commit()
    data = await state.get_data()
    await state.set_state(BroadcastNew.schedule)
    screen = await preview_screen(
        message.bot,
        session,
        user,
        data,
        has_channels=await _has_channel_target(session, list(data.get("chats", []))),
    )
    await send(message.bot, message.chat.id, screen, rich_buttons=_rich(user))


@router.message(BroadcastNew.buttons, F.text)
async def on_buttons(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    buttons = parse_buttons(message.text)
    if buttons is None:
        await send(
            message.bot, message.chat.id, Screen(ru.BROADCAST_BAD_BUTTONS), rich_buttons=_rich(user)
        )
        return
    data = await state.get_data()
    data["content"]["buttons"] = buttons
    await state.set_data(data)
    await _show_preview(message.chat.id, message.bot, session, user, state)


@router.callback_query(BroadcastNew.buttons, F.data == "bc:nobtn")
async def cb_no_buttons(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    await callback.answer()
    await _show_preview(callback.message.chat.id, callback.bot, session, user, state)


# --- when ------------------------------------------------------------------------


async def _create(
    session: AsyncSession, user: User, state: FSMContext, kind: BroadcastKind, **when
):
    data = await state.get_data()
    await state.clear()
    broadcast = await broadcast_service.create_broadcast(
        session,
        user,
        kind=kind,
        content=Content.from_json(data["content"]),
        chat_ids=data.get("chats", []),
        tz_name=_tz(),
        **when,
    )
    # The draft has become a real broadcast; keeping it would offer the
    # admin to "finish" something they have already sent.
    await broadcast_service.drop_draft(session, user)
    return broadcast


def _sent_screen(result: broadcast_delivery.RunResult) -> Screen:
    text = ru.BROADCAST_SENT_NOW.format(sent=result.sent, failed=result.failed)
    return Screen(
        text, rows=[[Btn(ru.BTN_BROADCAST_LIST, "bc:list")], [Btn(ru.BTN_BACK, "bc:menu")]]
    )


@router.callback_query(BroadcastNew.schedule, F.data == "bc:now")
async def cb_send_now(
    callback: CallbackQuery,
    session: AsyncSession,
    cache: Cache,
    user: User | None,
    state: FSMContext,
) -> None:
    if user is None:
        await callback.answer()
        return
    await callback.answer(ru.BROADCAST_RUNNING)
    broadcast = await _create(session, user, state, BroadcastKind.NOW)
    result = await broadcast_delivery.run_broadcast(session, callback.bot, broadcast, cache)
    await respond(callback, _sent_screen(result), rich_buttons=_rich(user))


@router.callback_query(BroadcastNew.schedule, F.data == "bc:at")
async def cb_send_at(callback: CallbackQuery, user: User | None, state: FSMContext) -> None:
    await state.set_state(BroadcastNew.datetime)
    screen = Screen(ru.BROADCAST_ASK_DATETIME.format(tz=_tz()), rows=[_leave_row("schedule")])
    await respond(callback, screen, rich_buttons=_rich(user))


@router.message(BroadcastNew.datetime, F.text)
async def on_datetime(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    when = parse_datetime(message.text, _tz())
    if when is None:
        await send(
            message.bot,
            message.chat.id,
            Screen(ru.BROADCAST_BAD_DATETIME),
            rich_buttons=_rich(user),
        )
        return
    broadcast = await _create(session, user, state, BroadcastKind.ONCE, scheduled_at=when)
    screen = Screen(
        ru.BROADCAST_SCHEDULED.format(when=format_local(broadcast.scheduled_at, _tz()), tz=_tz()),
        rows=[[Btn(ru.BTN_BROADCAST_LIST, "bc:list")], [Btn(ru.BTN_BACK, "bc:menu")]],
    )
    await send(message.bot, message.chat.id, screen, rich_buttons=_rich(user))


@router.callback_query(BroadcastNew.schedule, F.data == "bc:rec")
async def cb_send_recurring(callback: CallbackQuery, user: User | None, state: FSMContext) -> None:
    await state.set_state(BroadcastNew.days)
    await state.update_data(days=[])
    await respond(callback, days_screen(set()), rich_buttons=_rich(user))


@router.callback_query(BroadcastNew.days, F.data.regexp(r"^bc:d:(\d|all)$"))
async def cb_toggle_day(callback: CallbackQuery, user: User | None, state: FSMContext) -> None:
    data = await state.get_data()
    chosen = set(data.get("days", []))
    what = callback.data.rsplit(":", 1)[1]
    if what == "all":
        chosen = set() if len(chosen) == 7 else set(range(7))
    else:
        chosen.symmetric_difference_update({int(what)})
    await state.update_data(days=sorted(chosen))
    await respond(callback, days_screen(chosen), rich_buttons=_rich(user))


@router.callback_query(BroadcastNew.days, F.data == "bc:d:next")
async def cb_days_next(callback: CallbackQuery, user: User | None, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("days"):
        await callback.answer(ru.BROADCAST_NEED_DAYS, show_alert=True)
        return
    await state.set_state(BroadcastNew.time)
    screen = Screen(ru.BROADCAST_ASK_TIME.format(tz=_tz()), rows=[_leave_row("days")])
    await respond(callback, screen, rich_buttons=_rich(user))


@router.message(BroadcastNew.time, F.text)
async def on_time(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    at = parse_time(message.text)
    if at is None:
        await send(
            message.bot, message.chat.id, Screen(ru.BROADCAST_BAD_TIME), rich_buttons=_rich(user)
        )
        return
    data = await state.get_data()
    days = sorted(set(data.get("days", [])))
    broadcast = await _create(
        session, user, state, BroadcastKind.RECURRING, recur_days=days, recur_time=at
    )
    screen = Screen(
        ru.BROADCAST_RECURRING_SET.format(
            days=format_days(days),
            time=at.strftime("%H:%M"),
            tz=_tz(),
            next=format_local(broadcast.next_run_at, _tz()),
        ),
        rows=[[Btn(ru.BTN_BROADCAST_LIST, "bc:list")], [Btn(ru.BTN_BACK, "bc:menu")]],
    )
    await send(message.bot, message.chat.id, screen, rich_buttons=_rich(user))


# --- existing broadcasts ----------------------------------------------------------


@router.callback_query(F.data == "bc:list")
async def cb_list(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    await _keep_draft(session, user, state)
    await respond(callback, await list_screen(session, user), rich_buttons=_rich(user))


async def _owned(callback: CallbackQuery, session: AsyncSession, user: User) -> Broadcast | None:
    b = await broadcast_service.get_owned_broadcast(session, user, int(callback.data.split(":")[1]))
    if b is None:
        await callback.answer(ru.BROADCAST_NOT_FOUND, show_alert=True)
    return b


@router.callback_query(F.data.regexp(r"^bc:(\d+)$"))
async def cb_card(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    if user is None:
        await callback.answer()
        return
    b = await _owned(callback, session, user)
    if b is None:
        return
    await respond(callback, await card_screen(session, b), rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^bc:(\d+):preview$"))
async def cb_preview(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    if user is None:
        await callback.answer()
        return
    b = await _owned(callback, session, user)
    if b is None:
        return
    content = Content.from_json(b.content)
    await broadcast_delivery.send_content(
        callback.bot, callback.message.chat.id, content, content.file_id
    )
    await callback.answer()
    await send(
        callback.bot,
        callback.message.chat.id,
        await card_screen(session, b),
        rich_buttons=_rich(user),
    )


@router.callback_query(F.data.regexp(r"^bc:(\d+):(pause|resume)$"))
async def cb_pause_resume(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    b = await _owned(callback, session, user)
    if b is None:
        return
    if callback.data.endswith(":pause"):
        await broadcast_service.set_status(session, b, BroadcastStatus.PAUSED)
        await callback.answer(ru.BROADCAST_PAUSED)
    else:
        await broadcast_service.set_status(session, b, BroadcastStatus.SCHEDULED)
        await callback.answer(ru.BROADCAST_RESUMED)
    await respond(callback, await card_screen(session, b), rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^bc:(\d+):run$"))
async def cb_run_now(
    callback: CallbackQuery, session: AsyncSession, cache: Cache, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    b = await _owned(callback, session, user)
    if b is None:
        return
    await callback.answer(ru.BROADCAST_RUNNING)
    status_before = b.status
    result = await broadcast_delivery.run_broadcast(session, callback.bot, b, cache)
    if b.kind == BroadcastKind.RECURRING.value and status_before == BroadcastStatus.PAUSED.value:
        b.status = BroadcastStatus.PAUSED.value
        await session.commit()
    await send(
        callback.bot, callback.message.chat.id, _sent_screen(result), rich_buttons=_rich(user)
    )


# --- the published post: rewrite it, or take it down ----------------------


class BroadcastEdit(StatesGroup):
    text = State()


@router.callback_query(F.data.regexp(r"^bc:(\d+):edit$"))
async def cb_edit_post(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    b = await _owned(callback, session, user)
    if b is None:
        return
    standing = await post_service.messages_of(session, b.id)
    if not standing:
        await callback.answer(ru.BROADCAST_EDIT_NOTHING, show_alert=True)
        return
    await state.set_state(BroadcastEdit.text)
    await state.set_data({"broadcast_id": b.id})
    screen = Screen(
        ru.BROADCAST_ASK_EDIT.format(count=len(standing)),
        rows=[[Btn(ru.BTN_BACK, f"bc:{b.id}")]],
    )
    await respond(callback, screen, rich_buttons=_rich(user))


@router.message(BroadcastEdit.text)
async def on_edit_text(
    message: Message, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        return
    b = await broadcast_service.get_owned_broadcast(
        session, user, (await state.get_data())["broadcast_id"]
    )
    if b is None:
        await state.clear()
        return
    fresh = content_from_message(message)
    if fresh is None or fresh.text is None:
        await send(
            message.bot,
            message.chat.id,
            Screen(ru.BROADCAST_EDIT_UNSUPPORTED),
            rich_buttons=_rich(user),
        )
        return
    # Only the words change: the media file, the buttons and the delivery
    # options of the original post stay as they were.
    content = replace(
        Content.from_json(b.content),
        text=fresh.text,
        entities=fresh.entities,
        parse_mode=fresh.parse_mode,
    )
    published = broadcast_delivery.with_ad_label(content, broadcast_delivery.ad_label_of(user))
    result = await post_service.edit_all(message.bot, session, b, published)
    # Stored without the ad label, exactly as it was composed, so the next
    # run of a recurring broadcast appends it once and not twice.
    b.content = content.to_json()
    await session.commit()
    await state.clear()
    await send(
        message.bot,
        message.chat.id,
        Screen(
            ru.BROADCAST_EDITED.format(done=result.done, failed=result.failed),
            rows=[[Btn(ru.BTN_BACK, f"bc:{b.id}")]],
        ),
        rich_buttons=_rich(user),
    )


@router.callback_query(F.data.regexp(r"^bc:(\d+):delposts$"))
async def cb_delete_posts_confirm(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    b = await _owned(callback, session, user)
    if b is None:
        return
    standing = await post_service.messages_of(session, b.id)
    if not standing:
        await callback.answer(ru.BROADCAST_EDIT_NOTHING, show_alert=True)
        return
    screen = Screen(
        ru.BROADCAST_CONFIRM_DELETE_POSTS.format(count=len(standing)),
        rows=[
            [Btn(ru.BTN_POST_DELETE_YES, f"bc:{b.id}:delposts:yes", STYLE_DANGER)],
            [Btn(ru.BTN_BACK, f"bc:{b.id}")],
        ],
    )
    await respond(callback, screen, rich_buttons=_rich(user))


@router.callback_query(F.data.regexp(r"^bc:(\d+):delposts:yes$"))
async def cb_delete_posts(
    callback: CallbackQuery, session: AsyncSession, user: User | None
) -> None:
    if user is None:
        await callback.answer()
        return
    b = await _owned(callback, session, user)
    if b is None:
        return
    result = await post_service.delete_all(callback.bot, session, b)
    await callback.answer()
    await respond(
        callback,
        Screen(
            ru.BROADCAST_POSTS_DELETED.format(done=result.done, failed=result.failed),
            rows=[[Btn(ru.BTN_BACK, f"bc:{b.id}")]],
        ),
        rich_buttons=_rich(user),
    )


@router.callback_query(F.data.regexp(r"^bc:(\d+):del$"))
async def cb_delete(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    if user is None:
        await callback.answer()
        return
    b = await _owned(callback, session, user)
    if b is None:
        return
    await broadcast_service.set_status(session, b, BroadcastStatus.CANCELLED)
    await callback.answer(ru.BROADCAST_DELETED)
    await respond(callback, await list_screen(session, user), rich_buttons=_rich(user))
