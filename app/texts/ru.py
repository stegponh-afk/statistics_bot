"""Every user-facing string. Screens are HTML-ish (<b>, <i>, <code>,
<blockquote>) with a bold title on the first line and SEPARATOR lines that
app.ui.blocks turns into real dividers in rich messages."""

SEPARATOR = "━━━━━━━━━━━━━━━━━━━━"

# --- common buttons ---
BTN_BACK = "◀️ Назад"
BTN_MAIN_MENU = "🏠 Главное меню"
BTN_REFRESH = "🔄 Обновить"
BTN_CLOSE = "✖️ Закрыть"

# --- main menu ---
MAIN_MENU_TITLE = (
    "🤖 <b>Помощник админа</b>\n"
    f"{SEPARATOR}\n"
    "Статистика чатов, обязательная подписка на каналы и API для ваших ботов.\n\n"
    "Выберите раздел:"
)
BTN_MY_CHATS = "💬 Мои чаты"
BTN_API_KEYS = "🔑 API-ключи"
BTN_SETTINGS = "⚙️ Настройки"
BTN_HELP = "❓ Помощь"

# --- settings ---
SETTINGS_TITLE = "⚙️ <b>Настройки</b>"
BTN_MENU_STYLE = "🎨 Визуализация меню"
SETTINGS_MENU_STYLE_TITLE = (
    "🎨 <b>Визуализация меню</b>\n"
    f"{SEPARATOR}\n"
    "<b>Новый стиль</b> — кнопки встроены прямо в сообщение.\n"
    "<b>Старый стиль</b> — привычная клавиатура под сообщением."
)
BTN_MENU_STYLE_OLD = "📄 Старый стиль"
BTN_MENU_STYLE_NEW = "✨ Новый стиль"
SETTINGS_MENU_STYLE_SET_OLD = "Включён старый стиль"
SETTINGS_MENU_STYLE_SET_NEW = "Включён новый стиль"

# --- help ---
HELP_PRIVATE = (
    "❓ <b>Помощь</b>\n"
    f"{SEPARATOR}\n"
    "<b>Что умеет бот</b>\n"
    "· 📊 Статистика групп и каналов: сообщения за день/неделю/месяц, самые "
    "активные участники, популярные слова, активность по часам.\n"
    "· 🔒 Обязательная подписка в группе: сообщения неподписанных удаляются, "
    "а им приходит подсказка, которую видят только они.\n"
    "· 🔑 API для ваших ботов: одним HTTP-запросом узнать, подписан ли "
    "пользователь на ваши каналы.\n\n"
    "<b>Как подключить</b>\n"
    "1. Добавьте бота в группу и назначьте администратором "
    "(нужно право «Удалять сообщения»).\n"
    "2. Добавьте бота администратором в канал — иначе Telegram не даёт "
    "проверять подписку.\n"
    "3. Откройте «Мои чаты» и настройте нужный чат.\n\n"
    "<b>Команды в группе</b> (ответы видны только вам)\n"
    "· /stats — статистика чата (для админов)\n"
    "· /me — ваша личная активность\n"
    "· /help — эта справка"
)
HELP_GROUP = (
    "❓ <b>Помощь</b>\n"
    f"{SEPARATOR}\n"
    "Это сообщение видите только вы.\n\n"
    "· /me — ваша активность в этом чате\n"
    "· /stats — статистика чата (для администраторов)\n\n"
    "Настройки чата — в личных сообщениях с ботом, раздел «Мои чаты»."
)

# --- my chats ---
MY_CHATS_TITLE = "💬 <b>Мои чаты</b>"
MY_CHATS_EMPTY = (
    "💬 <b>Мои чаты</b>\n"
    f"{SEPARATOR}\n"
    "Пока ни одного чата.\n\n"
    "Добавьте бота в группу или канал <b>администратором</b> — чат появится "
    "здесь автоматически. Если бот уже добавлен, опубликуйте в чате любое сообщение "
    "или нажмите «Обновить»."
)
MY_CHATS_HINT = "Группы и каналы, где вы администратор и где есть бот:"
MY_CHATS_GROUPS = "<b>Группы</b>"
MY_CHATS_CHANNELS = "<b>Каналы</b>"
MY_CHATS_REFRESHED = "Список обновлён"

# --- stubs (replaced as features land) ---
COMING_SOON = "Раздел в разработке"

# --- chat card ---
CHAT_CARD = (
    "{icon} <b>{title}</b>\n"
    f"{SEPARATOR}\n"
    "Тип: {kind}\n"
    "Бот: {bot_status}\n"
    "{members_line}"
)
CHAT_KIND_GROUP = "группа"
CHAT_KIND_CHANNEL = "канал"
CHAT_BOT_ADMIN_FULL = "администратор ✅"
CHAT_BOT_ADMIN_NO_DELETE = "администратор, <i>нет права «Удалять сообщения»</i> ⚠️"
CHAT_BOT_MEMBER = "обычный участник ⚠️ (нужны права администратора)"
CHAT_BOT_GONE = "удалён из чата ❌"
CHAT_MEMBERS_LINE = "Участников: <b>{count}</b>\n"
CHAT_MEMBERS_UNKNOWN = ""
CHAT_REFRESHED = "Данные обновлены"
CHAT_NOT_FOUND = "Чат не найден или вы больше не его администратор"

BTN_CHAT_STATS = "📊 Статистика"
BTN_CHAT_FORCESUB_ON = "🔒 Обязательная подписка: ВКЛ"
BTN_CHAT_FORCESUB_OFF = "🔓 Обязательная подписка: ВЫКЛ"
BTN_CHAT_CHANNELS = "📣 Каналы ({count})"
BTN_CHAT_WHITELIST = "👤 Белый список ({count})"

# --- statistics ---
STATS_TITLE = "📊 <b>Статистика: {title}</b>"
STATS_OVERVIEW = (
    "📊 <b>Статистика: {title}</b>\n"
    f"{SEPARATOR}\n"
    "Сообщений сегодня: <b>{today}</b>\n"
    "За 7 дней: <b>{week}</b>\n"
    "За 30 дней: <b>{month}</b>\n"
    "Активных участников за 7 дней: <b>{active_week}</b>\n"
    "{members_line}"
    "\n<i>Часовой пояс: {tz}</i>"
)
STATS_TOP_USERS_TITLE = "👥 <b>Самые активные за 7 дней</b>"
STATS_TOP_WORDS_TITLE = "🔤 <b>Популярные слова за 7 дней</b>"
STATS_HOURS_TITLE = "🕒 <b>Активность по часам за 7 дней</b>"
STATS_EMPTY = "Пока нет данных — бот считает сообщения с момента добавления в чат."
STATS_ONLY_FOR_ADMINS = (
    "🔒 <b>Только для администраторов</b>\n"
    "Статистику чата могут смотреть его администраторы. "
    "Ваша личная активность — команда /me."
)
STATS_ONLY_FOR_ADMINS_TOAST = "Только для администраторов чата"
STATS_HOURS_ROW = "<code>{label}</code> {bar} {count}"
STATS_USER_ROW = "{medal} {name} — <b>{count}</b>"
STATS_WORD_ROW = "{n}. {word} — <b>{count}</b>"

BTN_STATS_OVERVIEW = "📊 Обзор"
BTN_STATS_USERS = "👥 Топ-5"
BTN_STATS_WORDS = "🔤 Слова"
BTN_STATS_HOURS = "🕒 Часы"

ME_TITLE = "👤 <b>Ваша активность</b>"
ME_BODY = (
    "👤 <b>Ваша активность</b>\n"
    f"{SEPARATOR}\n"
    "Чат: <b>{title}</b>\n\n"
    "Сегодня: <b>{today}</b>\n"
    "За 7 дней: <b>{week}</b>{rank_line}\n"
    "За 30 дней: <b>{month}</b>\n\n"
    "<i>Это сообщение видите только вы.</i>"
)
ME_RANK_LINE = " · место <b>#{rank}</b> из {active}"
ME_NO_USER = "Не удалось определить отправителя (анонимный режим?)."

# --- force-sub gate (shown ephemerally to the unsubscribed user) ---
GATE_PROMPT = (
    "🔒 <b>Подпишитесь, чтобы писать в чате</b>\n"
    f"{SEPARATOR}\n"
    "Чтобы отправлять сообщения в «{title}», нужно быть подписанным на:\n"
    "{channels}\n\n"
    "После подписки нажмите «Проверить».\n"
    "<i>Это сообщение видите только вы.</i>"
)
GATE_CHANNEL_LINE = "· {title}"
GATE_CHANNEL_NO_LINK = " <i>(ссылку получить не удалось — попросите админа)</i>"
GATE_BTN_SUBSCRIBE = "➕ {title}"
GATE_BTN_CHECK = "✅ Проверить"
GATE_OK = "✅ <b>Готово</b>\n" f"{SEPARATOR}\n" "Подписка найдена — теперь вы можете писать в чате."
GATE_STILL_MISSING = "Подписка пока не найдена"
GATE_TOO_FAST = "Подождите пару секунд и попробуйте снова"
GATE_LOST_RIGHTS_DM = (
    "⚠️ В чате «{title}» бот потерял право удалять сообщения, "
    "поэтому обязательная подписка отключена. Верните право и включите её снова в «Мои чаты»."
)

# --- channels binding (private) ---
CHANNELS_TITLE = (
    "📣 <b>Обязательные каналы</b>\n"
    f"{SEPARATOR}\n"
    "Чат: <b>{title}</b>\n"
    "Отметьте каналы, на которые должны быть подписаны участники:"
)
CHANNELS_EMPTY = (
    "📣 <b>Обязательные каналы</b>\n"
    f"{SEPARATOR}\n"
    "Чат: <b>{title}</b>\n\n"
    "У вас пока нет каналов, доступных боту.\n\n"
    "Добавьте бота <b>администратором</b> в свой канал — "
    "без этого Telegram не позволяет проверять подписку. Затем нажмите «Обновить»."
)
CHANNEL_ROW_ON = "✅ {title}"
CHANNEL_ROW_OFF = "☐ {title}"
CHANNEL_BOT_NOT_ADMIN = "Бот больше не администратор канала «{title}» — добавьте его снова"
CHANNEL_ADDED = "Канал добавлен"
CHANNEL_REMOVED = "Канал убран"

FORCESUB_ENABLED = "Обязательная подписка включена"
FORCESUB_DISABLED = "Обязательная подписка выключена"
FORCESUB_NEED_CHANNELS = "Сначала отметьте хотя бы один канал в разделе «Каналы»"
FORCESUB_NEED_DELETE_RIGHT = (
    "Боту нужно право «Удалять сообщения» в этом чате. Выдайте его и нажмите «Обновить»."
)

# --- whitelist (private) ---
WHITELIST_TITLE = (
    "👤 <b>Белый список</b>\n"
    f"{SEPARATOR}\n"
    "Чат: <b>{title}</b>\n"
    "Эти участники могут писать без подписки:"
)
WHITELIST_EMPTY_LINE = "<i>Пока никого. Администраторы чата пропускаются всегда.</i>"
WHITELIST_ROW = "🗑 {name}"
BTN_WHITELIST_ADD = "➕ Добавить"
WHITELIST_ASK = (
    "👤 <b>Добавить в белый список</b>\n"
    f"{SEPARATOR}\n"
    "Пришлите <b>ID пользователя</b> числом или <b>перешлите</b> сюда его сообщение.\n"
    "Если у пользователя скрыта пересылка, подойдёт только ID."
)
WHITELIST_BAD_INPUT = "Не понял. Нужен числовой ID или пересланное сообщение пользователя."
WHITELIST_ADDED = "Добавлен в белый список"
WHITELIST_ALREADY = "Уже в белом списке"
WHITELIST_REMOVED = "Удалён из белого списка"
WHITELIST_CMD_NEED_REPLY = (
    "Команду /whitelist нужно отправить <b>ответом</b> на сообщение пользователя."
)
WHITELIST_CMD_ADDED = "✅ <b>{name}</b> добавлен в белый список — может писать без подписки."
BTN_CANCEL = "✖️ Отмена"

# --- API keys (private) ---
KEYS_TITLE = (
    "🔑 <b>API-ключи</b>\n"
    f"{SEPARATOR}\n"
    "Ключ позволяет вашему боту одним HTTP-запросом узнать, подписан ли "
    "пользователь на ваши каналы. Каналы привязываются к ключу."
)
KEYS_EMPTY_LINE = "<i>Пока ни одного ключа.</i>"
KEY_ROW = "🔑 {name} · {prefix}…"
BTN_KEY_NEW = "➕ Создать ключ"
BTN_KEY_HOWTO = "📖 Как подключить"
KEY_ASK_NAME = (
    "🔑 <b>Новый ключ</b>\n"
    f"{SEPARATOR}\n"
    "Как назвать ключ? Например, имя вашего бота.\n"
    "Отправьте название (до 64 символов)."
)
KEY_CREATED = (
    "✅ <b>Ключ создан</b>\n"
    f"{SEPARATOR}\n"
    "Название: <b>{name}</b>\n\n"
    "Скопируйте ключ — он показывается <b>только сейчас</b>:\n"
    "<code>{raw}</code>\n\n"
    "Теперь привяжите к ключу каналы («Каналы») и подключите бота («Как подключить»)."
)
KEY_ROTATED = (
    "🔁 <b>Ключ перевыпущен</b>\n"
    f"{SEPARATOR}\n"
    "Старый ключ больше не работает. Новый ключ (показывается только сейчас):\n"
    "<code>{raw}</code>"
)
KEY_CARD = (
    "🔑 <b>{name}</b>\n"
    f"{SEPARATOR}\n"
    "Ключ: <code>{prefix}…</code>\n"
    "Создан: {created}\n"
    "Последний запрос: {last_used}\n"
    "Всего запросов: <b>{requests}</b>\n"
    "Каналов привязано: <b>{channels}</b>"
)
KEY_NEVER_USED = "ещё не было"
BTN_KEY_CHANNELS = "📣 Каналы ({count})"
BTN_KEY_ROTATE = "🔁 Перевыпустить"
BTN_KEY_DELETE = "🗑 Удалить"
KEY_DELETED = "Ключ удалён"
KEY_NOT_FOUND = "Ключ не найден"
KEY_NAME_TOO_LONG = "Слишком длинно — до 64 символов."
KEY_CHANNELS_TITLE = (
    "📣 <b>Каналы ключа «{name}»</b>\n"
    f"{SEPARATOR}\n"
    "Отметьте каналы, подписку на которые будет проверять этот ключ:"
)
KEY_CHANNELS_EMPTY = (
    "📣 <b>Каналы ключа «{name}»</b>\n"
    f"{SEPARATOR}\n"
    "У вас пока нет каналов, доступных боту.\n\n"
    "Добавьте бота <b>администратором</b> в свой канал — "
    "без этого Telegram не позволяет проверять подписку. Затем нажмите «Обновить»."
)
KEY_HOWTO = (
    "📖 <b>Как подключить свой бот</b>\n"
    f"{SEPARATOR}\n"
    "1. Добавьте этого бота администратором в ваши каналы.\n"
    "2. Создайте ключ и отметьте в нём каналы.\n"
    "3. Из своего бота перед выдачей контента делайте запрос:\n"
    "<code>GET {base}/v1/check?user_id=ID_ПОЛЬЗОВАТЕЛЯ</code>\n"
    "с заголовком <code>Authorization: Bearer ВАШ_КЛЮЧ</code>\n\n"
    "Ответ:\n"
    '<code>{{"ok": true, "subscribed": false, "missing": [{{"chat_id": -100…, '
    '"title": "Канал", "invite_link": "https://t.me/…"}}]}}</code>\n\n'
    "Если <code>subscribed</code> = false — покажите пользователю кнопки со ссылками "
    "из <code>missing</code> и повторите запрос после подписки.\n\n"
    "Результат кэшируется ~60 секунд; добавьте <code>&force=1</code>, "
    "чтобы проверить заново (например, по кнопке «Проверить»).\n"
    "Лимит: {limit} запросов в минуту на ключ.\n"
    "<code>GET {base}/v1/channels</code> — список каналов ключа для отрисовки кнопок."
)

# --- owner overview (/admin, OWNER_IDS only) ---
ADMIN_OVERVIEW = (
    "🛠 <b>Сводка бота</b>\n"
    f"{SEPARATOR}\n"
    "Пользователей: <b>{users}</b>\n"
    "Чатов с ботом: <b>{chats}</b> (групп: {groups}, каналов: {channels})\n"
    "Гейт включён в: <b>{gated}</b>\n"
    "Активных API-ключей: <b>{keys}</b>\n"
    "Событий сообщений в базе: <b>{events}</b>"
)
