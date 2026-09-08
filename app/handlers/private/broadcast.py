"""«Рассылка»: compose a message, pick chats/bots, send now / at a time /
on a weekly schedule; list and manage existing broadcasts.

  bc:menu                  the section
  bc:new                   start composing (FSM)
  bc:t:c:{chat_id}         toggle a chat target      bc:t:b:{key_id}  toggle a bot
  bc:t:next                targets chosen -> ask for the message
  bc:nobtn                 skip buttons -> preview
  bc:now | bc:at | bc:rec  choose when
  bc:d:{0..6} | bc:d:all | bc:d:next   weekday toggles for recurring
  bc:list                  my broadcasts
  bc:{id}                  one broadcast; :preview :pause :resume :run :del
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Broadcast, BroadcastKind, BroadcastStatus, User
from app.services import api_key_service, audience_service, broadcast_delivery, broadcast_service
from app.services.broadcast_service import (
    WEEKDAY_LABELS,
    Content,
    content_from_message,
    format_days,
    format_local,
    parse_buttons,
    parse_datetime,
    parse_time,
)
from app.services.chat_service import list_admin_chats
from app.texts import ru
from app.ui import Btn, Screen, respond, send
from app.ui.blocks import strip_tags
from app.ui.buttons import STYLE_DANGER, STYLE_PRIMARY, STYLE_SUCCESS
from config import settings

router = Router(name="broadcast")


class BroadcastNew(StatesGroup):
    targets = State()
    message = State()
    buttons = State()
    schedule = State()
    datetime = State()
    days = State()
    time = State()


def _rich(user: User | None) -> bool:
    return user.rich_buttons_enabled if user else True


def _tz() -> str:
    return settings.default_timezone


# --- screens --------------------------------------------------------------


def menu_screen() -> Screen:
    return Screen(
        ru.BROADCAST_MENU,
        rows=[
            [Btn(ru.BTN_BROADCAST_NEW, "bc:new"), Btn(ru.BTN_BROADCAST_LIST, "bc:list")],
            [Btn(ru.BTN_BACK, "menu:main")],
        ],
    )


async def _available_targets(session: AsyncSession, user: User):
    chats = [c for c in await list_admin_chats(session, user) if c.is_active]
    bots = await api_key_service.list_bot_keys(session, user)
    return chats, bots


async def targets_screen(
    session: AsyncSession, user: User, chosen_chats: set[int], chosen_bots: set[int]
) -> Screen:
    chats, bots = await _available_targets(session, user)
    rows: list[list[Btn]] = []
    for chat in chats:
        icon = "📣" if chat.is_channel else "👥"
        title = f"{icon} {chat.title or chat.telegram_id}"
        label = (
            ru.BROADCAST_TARGET_ON if chat.id in chosen_chats else ru.BROADCAST_TARGET_OFF
        ).format(title=title)
        rows.append([Btn(label, f"bc:t:c:{chat.id}")])
    for key in bots:
        reachable, _ = await audience_service.audience_size(session, key)
        title = ru.BROADCAST_TARGET_BOT.format(name=key.name, audience=reachable)
        label = (
            ru.BROADCAST_TARGET_ON if key.id in chosen_bots else ru.BROADCAST_TARGET_OFF
        ).format(title=title)
        rows.append([Btn(label, f"bc:t:b:{key.id}")])
    rows.append([Btn(ru.BTN_NEXT, "bc:t:next", STYLE_PRIMARY)])
    rows.append([Btn(ru.BTN_CANCEL, "bc:menu", STYLE_DANGER)])
    count = len(chosen_chats) + len(chosen_bots)
    return Screen(ru.BROADCAST_PICK_TARGETS.format(count=count), rows=rows)


def days_screen(chosen: set[int]) -> Screen:
    day_buttons = [
        Btn(("✅ " if d in chosen else "") + WEEKDAY_LABELS[d], f"bc:d:{d}") for d in range(7)
    ]
    rows = [day_buttons[:4], day_buttons[4:], [Btn(ru.BTN_EVERY_DAY, "bc:d:all")]]
    rows.append([Btn(ru.BTN_NEXT, "bc:d:next", STYLE_PRIMARY)])
    rows.append([Btn(ru.BTN_CANCEL, "bc:menu", STYLE_DANGER)])
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
    chats, keys = await broadcast_service.targets(session, b)
    target_names = [c.title or str(c.telegram_id) for c in chats] + [f"🤖 {k.name}" for k in keys]
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
    rows = [[Btn(ru.BTN_BROADCAST_PREVIEW, f"bc:{b.id}:preview")]]
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
async def cmd_broadcast(message: Message, user: User | None, state: FSMContext) -> None:
    if user is None:
        return
    await state.clear()
    await send(message.bot, message.chat.id, menu_screen(), rich_buttons=_rich(user))


@router.callback_query(F.data == "bc:menu")
async def cb_menu(callback: CallbackQuery, user: User | None, state: FSMContext) -> None:
    await state.clear()
    await respond(callback, menu_screen(), rich_buttons=_rich(user))


@router.callback_query(F.data == "bc:new")
async def cb_new(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    chats, bots = await _available_targets(session, user)
    if not chats and not bots:
        await respond(
            callback,
            Screen(ru.BROADCAST_NO_TARGETS, rows=[[Btn(ru.BTN_BACK, "bc:menu")]]),
            rich_buttons=_rich(user),
        )
        return
    await state.set_state(BroadcastNew.targets)
    await state.set_data({"chats": [], "bots": []})
    await respond(
        callback, await targets_screen(session, user, set(), set()), rich_buttons=_rich(user)
    )


@router.callback_query(BroadcastNew.targets, F.data.regexp(r"^bc:t:(c|b):(\d+)$"))
async def cb_toggle_target(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    _, _, kind, raw_id = callback.data.split(":")
    target_id = int(raw_id)
    data = await state.get_data()
    bucket = "chats" if kind == "c" else "bots"
    chosen = set(data.get(bucket, []))
    chosen.symmetric_difference_update({target_id})
    data[bucket] = sorted(chosen)
    await state.set_data(data)
    await respond(
        callback,
        await targets_screen(session, user, set(data["chats"]), set(data["bots"])),
        rich_buttons=_rich(user),
    )


@router.callback_query(BroadcastNew.targets, F.data == "bc:t:next")
async def cb_targets_next(callback: CallbackQuery, user: User | None, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("chats") and not data.get("bots"):
        await callback.answer(ru.BROADCAST_NEED_TARGET, show_alert=True)
        return
    await state.set_state(BroadcastNew.message)
    screen = Screen(ru.BROADCAST_ASK_MESSAGE, rows=[[Btn(ru.BTN_CANCEL, "bc:menu", STYLE_DANGER)]])
    await respond(callback, screen, rich_buttons=_rich(user))


@router.message(BroadcastNew.message)
async def on_message_content(message: Message, user: User | None, state: FSMContext) -> None:
    if user is None:
        return
    content = content_from_message(message)
    if content is None:
        await send(
            message.bot, message.chat.id, Screen(ru.BROADCAST_UNSUPPORTED), rich_buttons=_rich(user)
        )
        return
    await state.update_data(content=content.to_json())
    await state.set_state(BroadcastNew.buttons)
    screen = Screen(
        ru.BROADCAST_ASK_BUTTONS,
        rows=[[Btn(ru.BTN_NO_BUTTONS, "bc:nobtn")], [Btn(ru.BTN_CANCEL, "bc:menu", STYLE_DANGER)]],
    )
    await send(message.bot, message.chat.id, screen, rich_buttons=_rich(user))


async def _show_preview(chat_id: int, bot, user: User, state: FSMContext) -> None:
    data = await state.get_data()
    content = Content.from_json(data["content"])
    await broadcast_delivery._send(bot, chat_id, content, content.file_id)
    targets = len(data.get("chats", [])) + len(data.get("bots", []))
    screen = Screen(
        ru.BROADCAST_PREVIEW_HINT.format(targets=targets),
        rows=[
            [Btn(ru.BTN_SEND_NOW, "bc:now", STYLE_SUCCESS)],
            [Btn(ru.BTN_SEND_AT, "bc:at")],
            [Btn(ru.BTN_SEND_RECURRING, "bc:rec")],
            [Btn(ru.BTN_CANCEL, "bc:menu", STYLE_DANGER)],
        ],
    )
    await state.set_state(BroadcastNew.schedule)
    await send(bot, chat_id, screen, rich_buttons=_rich(user))


@router.message(BroadcastNew.buttons, F.text)
async def on_buttons(message: Message, user: User | None, state: FSMContext) -> None:
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
    await _show_preview(message.chat.id, message.bot, user, state)


@router.callback_query(BroadcastNew.buttons, F.data == "bc:nobtn")
async def cb_no_buttons(callback: CallbackQuery, user: User | None, state: FSMContext) -> None:
    if user is None:
        await callback.answer()
        return
    await callback.answer()
    await _show_preview(callback.message.chat.id, callback.bot, user, state)


# --- when ------------------------------------------------------------------------


async def _create(
    session: AsyncSession, user: User, state: FSMContext, kind: BroadcastKind, **when
):
    data = await state.get_data()
    await state.clear()
    return await broadcast_service.create_broadcast(
        session,
        user,
        kind=kind,
        content=Content.from_json(data["content"]),
        chat_ids=data.get("chats", []),
        bot_key_ids=data.get("bots", []),
        tz_name=_tz(),
        **when,
    )


def _sent_screen(result: broadcast_delivery.RunResult) -> Screen:
    text = ru.BROADCAST_SENT_NOW.format(
        sent=result.sent,
        failed=result.failed,
        blocked_line=ru.BROADCAST_BLOCKED_LINE.format(blocked=result.blocked)
        if result.blocked
        else "",
    )
    return Screen(
        text, rows=[[Btn(ru.BTN_BROADCAST_LIST, "bc:list")], [Btn(ru.BTN_BACK, "bc:menu")]]
    )


@router.callback_query(BroadcastNew.schedule, F.data == "bc:now")
async def cb_send_now(
    callback: CallbackQuery, session: AsyncSession, user: User | None, state: FSMContext
) -> None:
    if user is None:
        await callback.answer()
        return
    await callback.answer(ru.BROADCAST_RUNNING)
    broadcast = await _create(session, user, state, BroadcastKind.NOW)
    result = await broadcast_delivery.run_broadcast(session, callback.bot, broadcast)
    await respond(callback, _sent_screen(result), rich_buttons=_rich(user))


@router.callback_query(BroadcastNew.schedule, F.data == "bc:at")
async def cb_send_at(callback: CallbackQuery, user: User | None, state: FSMContext) -> None:
    await state.set_state(BroadcastNew.datetime)
    screen = Screen(
        ru.BROADCAST_ASK_DATETIME.format(tz=_tz()),
        rows=[[Btn(ru.BTN_CANCEL, "bc:menu", STYLE_DANGER)]],
    )
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
    screen = Screen(
        ru.BROADCAST_ASK_TIME.format(tz=_tz()), rows=[[Btn(ru.BTN_CANCEL, "bc:menu", STYLE_DANGER)]]
    )
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
    await state.clear()
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
    await broadcast_delivery._send(callback.bot, callback.message.chat.id, content, content.file_id)
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
async def cb_run_now(callback: CallbackQuery, session: AsyncSession, user: User | None) -> None:
    if user is None:
        await callback.answer()
        return
    b = await _owned(callback, session, user)
    if b is None:
        return
    await callback.answer(ru.BROADCAST_RUNNING)
    status_before = b.status
    result = await broadcast_delivery.run_broadcast(session, callback.bot, b)
    if b.kind == BroadcastKind.RECURRING.value and status_before == BroadcastStatus.PAUSED.value:
        b.status = BroadcastStatus.PAUSED.value
        await session.commit()
    await send(
        callback.bot, callback.message.chat.id, _sent_screen(result), rich_buttons=_rich(user)
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
