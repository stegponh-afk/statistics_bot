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
    "Статистика чатов, обязательная подписка на каналы, API и рассылки для ваших ботов.\n\n"
    "Выберите раздел:"
)
BTN_MY_CHATS = "💬 Чаты"
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
    "<code>{raw}</code>\n\n"
    "Ссылка для конструктора ботов:\n<code>{check_url}</code>"
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
    "с заголовком <code>Authorization: Bearer ВАШ_КЛЮЧ</code>\n"
    "или, если конструктор не умеет заголовки, ключ прямо в ссылке:\n"
    "<code>GET {base}/v1/check/ВАШ_КЛЮЧ?user_id=ID_ПОЛЬЗОВАТЕЛЯ</code>\n\n"
    "<b>Без кода вообще</b>: на карточке канала («Чаты» → канал) есть «Награда за "
    "подписку» — бот сам проверит подписку и выдаст материал, вашему боту ничего "
    "делать не нужно.\n\n"
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

# --- bots (the owner's own bots: API key + token + audience) ---
BTN_MY_BOTS = "🤖 Боты"
BTN_BROADCAST = "📨 Рассылка"
BOTS_TITLE = (
    "🤖 <b>Боты</b>\n"
    f"{SEPARATOR}\n"
    "Ваши боты. У каждого есть API-ключ для проверки подписки, а с токеном бот "
    "может получать рассылки для своих пользователей."
)
BOTS_EMPTY_LINE = "<i>Пока ни одного бота.</i>"
BOT_ROW = "🤖 {name}"
BTN_BOT_NEW = "➕ Добавить бота"
BOT_ASK_NAME = (
    "🤖 <b>Новый бот</b>\n"
    f"{SEPARATOR}\n"
    "Как назвать бота? Например, его @username.\n"
    "Отправьте название (до 64 символов)."
)
BOT_CREATED = (
    "✅ <b>Бот добавлен</b>\n"
    f"{SEPARATOR}\n"
    "Название: <b>{name}</b>\n\n"
    "API-ключ для проверки подписки — скопируйте, он показывается <b>только сейчас</b>:\n"
    "<code>{raw}</code>\n\n"
    "Готовая ссылка для конструктора ботов (подставьте ID пользователя):\n"
    "<code>{check_url}</code>\n\n"
    "Дальше: привяжите каналы («Каналы»), а для рассылок добавьте токен бота."
)
BOT_CARD = (
    "🤖 <b>{name}</b>\n"
    f"{SEPARATOR}\n"
    "API-ключ: <code>{prefix}…</code> · запросов: <b>{requests}</b>\n"
    "Последний запрос: {last_used}\n"
    "Каналов для проверки: <b>{channels}</b>\n"
    "Токен: {token_line}\n"
    "Аудитория для рассылок: <b>{audience}</b>{blocked_line}"
)
BOT_TOKEN_SET = "добавлен (@{username})"
BOT_TOKEN_MISSING = "не добавлен — рассылки недоступны"
BOT_BLOCKED_LINE = " (заблокировали бота: {blocked})"
BTN_BOT_TOKEN_ADD = "🔐 Добавить токен"
BTN_BOT_TOKEN_REMOVE = "🔐 Убрать токен"
BOT_ASK_TOKEN = (
    "🔐 <b>Токен бота</b>\n"
    f"{SEPARATOR}\n"
    "Пришлите токен вашего бота из @BotFather (вида <code>123456:ABC…</code>).\n\n"
    "Токен нужен, чтобы рассылки уходили пользователям <b>от имени вашего бота</b>. "
    "Он хранится в базе этого сервиса — добавляйте, только если доверяете ему. "
    "Сообщение с токеном будет удалено."
)
BOT_TOKEN_INVALID = "Токен не подошёл: Telegram его не принял. Проверьте и пришлите ещё раз."
BOT_TOKEN_SAVED = "Токен сохранён: @{username}"
BOT_TOKEN_REMOVED = "Токен удалён"
BOT_AUDIENCE_HINT = (
    "Аудитория — пользователи вашего бота, которых он проверял через "
    "<code>/v1/check</code> или зарегистрировал через <code>POST /v1/users</code>."
)
KEY_HOWTO_USERS = (
    "\n\n<b>Аудитория для рассылок</b>\n"
    "Каждый пользователь, проверенный через <code>/v1/check</code>, попадает в аудиторию. "
    "Чтобы добавить остальных, отправьте\n"
    '<code>POST {base}/v1/users</code> с телом <code>{{"user_ids": [1, 2, 3]}}</code> '
    "(до 10 000 за раз)."
)

# --- broadcasts ---
BROADCAST_MENU = (
    "📨 <b>Рассылка</b>\n"
    f"{SEPARATOR}\n"
    "Отправляйте сообщения в свои чаты и пользователям своих ботов: "
    "сразу, к заданному времени или по расписанию."
)
BTN_BROADCAST_NEW = "✉️ Новая рассылка"
BTN_BROADCAST_LIST = "📋 Мои рассылки"
BROADCAST_NO_TARGETS = (
    "📨 <b>Рассылка</b>\n"
    f"{SEPARATOR}\n"
    "Пока некуда рассылать: добавьте бота в свои чаты администратором "
    "или добавьте токен своего бота в разделе «Боты»."
)
BROADCAST_PICK_TARGETS = (
    "📨 <b>Куда отправить?</b>\n" f"{SEPARATOR}\n" "Отметьте чаты и ботов. Выбрано: <b>{count}</b>"
)
BROADCAST_TARGET_ON = "✅ {title}"
BROADCAST_TARGET_OFF = "☐ {title}"
BROADCAST_TARGET_BOT = "🤖 {name} ({audience} чел.)"
BTN_NEXT = "Далее ➡️"
BROADCAST_NEED_TARGET = "Отметьте хотя бы один чат или бота"
BROADCAST_ASK_MESSAGE = (
    "✉️ <b>Сообщение</b>\n"
    f"{SEPARATOR}\n"
    "Пришлите сообщение для рассылки: текст или фото/видео/файл с подписью.\n\n"
    "Форматирование — как в Telegram (выделите текст → Жирный и т.д.) "
    "или markdown-разметкой:\n"
    "<code>**жирный**</code> · <code>_курсив_</code> · <code>__подчёркнутый__</code> · "
    "<code>~~зачёркнутый~~</code> · <code>||спойлер||</code> · <code>`код`</code> · "
    "<code>[текст](https://ссылка)</code> · строки с <code>&gt;</code> — цитата."
)
BROADCAST_UNSUPPORTED = (
    "Такой тип сообщения не поддерживается. "
    "Пришлите текст, фото, видео, файл, GIF, аудио или голосовое."
)
BROADCAST_ASK_BUTTONS = (
    "🔗 <b>Кнопки</b>\n"
    f"{SEPARATOR}\n"
    "Добавить кнопки-ссылки под сообщением? Пришлите по одной на строку:\n"
    "<code>Текст кнопки | https://ссылка</code>\n\n"
    "Или нажмите «Без кнопок»."
)
BTN_NO_BUTTONS = "Без кнопок"
BROADCAST_BAD_BUTTONS = "Не разобрал. Формат каждой строки: <code>Текст | https://ссылка</code>"
BROADCAST_PREVIEW_HINT = (
    "👀 <b>Так будет выглядеть рассылка</b> (сообщение выше)\n"
    f"{SEPARATOR}\n"
    "Получателей: <b>{targets}</b>\n\n"
    "Когда отправить?"
)
BTN_SEND_NOW = "🚀 Прямо сейчас"
BTN_SEND_AT = "🕒 К определённому времени"
BTN_SEND_RECURRING = "🔁 Циклично"
BROADCAST_ASK_DATETIME = (
    "🕒 <b>Когда отправить?</b>\n"
    f"{SEPARATOR}\n"
    "Пришлите дату и время: <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
    "или просто <code>ЧЧ:ММ</code> — на сегодня (если время прошло — на завтра).\n"
    "Часовой пояс: {tz}"
)
BROADCAST_BAD_DATETIME = "Не разобрал или время уже прошло. Пример: <code>15.09.2026 18:30</code>"
BROADCAST_PICK_DAYS = (
    "🔁 <b>В какие дни повторять?</b>\n"
    f"{SEPARATOR}\n"
    "Отметьте дни недели. Выбрано: <b>{days}</b>"
)
BTN_EVERY_DAY = "Каждый день"
BROADCAST_NEED_DAYS = "Отметьте хотя бы один день"
BROADCAST_ASK_TIME = (
    "🕒 <b>Во сколько?</b>\n"
    f"{SEPARATOR}\n"
    "Пришлите время в формате <code>ЧЧ:ММ</code>. Часовой пояс: {tz}"
)
BROADCAST_BAD_TIME = "Нужно время в формате <code>ЧЧ:ММ</code>, например <code>09:30</code>"
BROADCAST_SENT_NOW = (
    "🚀 <b>Рассылка отправлена</b>\n"
    f"{SEPARATOR}\n"
    "Доставлено: <b>{sent}</b>\n"
    "Не доставлено: <b>{failed}</b>{blocked_line}"
)
BROADCAST_BLOCKED_LINE = "\nЗаблокировали бота: <b>{blocked}</b>"
BROADCAST_SCHEDULED = (
    "🕒 <b>Рассылка запланирована</b>\n" f"{SEPARATOR}\n" "Отправится: <b>{when}</b> ({tz})"
)
BROADCAST_RECURRING_SET = (
    "🔁 <b>Циклическая рассылка создана</b>\n"
    f"{SEPARATOR}\n"
    "Дни: <b>{days}</b> в <b>{time}</b> ({tz})\n"
    "Ближайшая отправка: <b>{next}</b>"
)
BROADCASTS_TITLE = "📋 <b>Мои рассылки</b>"
BROADCASTS_EMPTY_LINE = "<i>Пока нет рассылок.</i>"
BROADCAST_ROW = "{icon} {title}"
BROADCAST_KIND_NOW = "сразу"
BROADCAST_KIND_ONCE = "к времени"
BROADCAST_KIND_RECURRING = "циклично"
BROADCAST_STATUS = {
    "scheduled": "⏳ ожидает",
    "paused": "⏸ на паузе",
    "done": "✅ отправлена",
    "cancelled": "✖️ отменена",
}
BROADCAST_CARD = (
    "📨 <b>Рассылка #{id}</b>\n"
    f"{SEPARATOR}\n"
    "Тип: <b>{kind}</b> · {status}\n"
    "Получатели: {targets}\n"
    "{schedule_line}"
    "Отправок: <b>{runs}</b> · доставлено: <b>{sent}</b> · не доставлено: <b>{failed}</b>\n"
    "Последняя отправка: {last_run}\n\n"
    "<i>Текст: {snippet}</i>"
)
BROADCAST_SCHEDULE_ONCE = "Когда: <b>{when}</b> ({tz})\n"
BROADCAST_SCHEDULE_RECURRING = (
    "Расписание: <b>{days}</b> в <b>{time}</b> ({tz}), ближайшая: <b>{next}</b>\n"
)
BTN_BROADCAST_PAUSE = "⏸ Пауза"
BTN_BROADCAST_RESUME = "▶️ Возобновить"
BTN_BROADCAST_RUN_NOW = "🚀 Отправить сейчас"
BTN_BROADCAST_DELETE = "🗑 Удалить"
BTN_BROADCAST_PREVIEW = "👀 Показать сообщение"
BROADCAST_DELETED = "Рассылка удалена"
BROADCAST_PAUSED = "Рассылка на паузе"
BROADCAST_RESUMED = "Рассылка возобновлена"
BROADCAST_NOT_FOUND = "Рассылка не найдена"
BROADCAST_RUNNING = "Отправляю…"

# --- owner admin menu (/admin, OWNER_IDS only) ---
BTN_ADMIN = "🛠 Админ"
BTN_ADMIN_CHANNELS = "📣 Каналы"
BTN_ADMIN_GROUPS = "👥 Группы"
BTN_ADMIN_BOTS = "🤖 Боты"
ADMIN_OVERVIEW = (
    "🛠 <b>Сводка</b>\n"
    f"{SEPARATOR}\n"
    "<b>Пользователи бота</b>\n"
    "Всего в базе: <b>{users_total}</b> · запустили бота: <b>{users_started}</b>\n"
    "Новых сегодня: <b>{users_new_today}</b> · за 7 дней: <b>{users_new_week}</b>\n\n"
    "<b>Каналы</b>: <b>{channels}</b> · подписчиков суммарно: <b>{channel_members}</b>\n"
    "<b>Группы</b>: <b>{groups}</b> · участников суммарно: <b>{group_members}</b>\n\n"
    "<b>Боты</b>: <b>{bots}</b> · с токеном: <b>{bots_with_token}</b>\n"
    "Аудитория ботов: <b>{audience_total}</b> · уникальных: <b>{audience_distinct}</b>\n"
    "API-запросов всего: <b>{api_requests}</b>\n\n"
    "Рассылок в очереди: <b>{broadcasts}</b> · событий сообщений: <b>{events}</b>"
)
ADMIN_CHANNELS_TITLE = "📣 <b>Каналы</b>"
ADMIN_GROUPS_TITLE = "👥 <b>Группы</b>"
ADMIN_BOTS_TITLE = "🤖 <b>Боты</b>"
ADMIN_LIST_EMPTY = "<i>Пусто.</i>"
ADMIN_LIST_MORE = "<i>…и ещё {count}</i>"
ADMIN_CHAT_ROW = "· <b>{title}</b>{username} — {members} чел. · админ: {owner}"
ADMIN_BOT_ROW = (
    "· <b>{name}</b>{bot} — аудитория {audience} · каналов {channels} · "
    "запросов {requests} · владелец: {owner}"
)

# --- channel comments gate (channel card) ---
CHAT_COMMENTS_LINE = "Комментарии: {value}\n"
CHAT_COMMENTS_GROUP = "группа «{title}»"
CHAT_COMMENTS_GATE_ON = " · подписка обязательна ✅"
CHAT_COMMENTS_NO_DISCUSSION = "обсуждения не подключены"
CHAT_COMMENTS_BOT_MISSING = (
    "есть группа обсуждений, но бот в неё не добавлен — добавьте его туда администратором"
)
BTN_CHAT_COMMENTS_GATE_ON = "🔒 Подписка в комментариях: ВКЛ"
BTN_CHAT_COMMENTS_GATE_OFF = "🔓 Подписка в комментариях: ВЫКЛ"
COMMENTS_GATE_NO_GROUP = (
    "У канала нет группы обсуждений с ботом. Подключите обсуждения в настройках канала "
    "и добавьте бота в эту группу администратором с правом «Удалять сообщения»."
)
COMMENTS_GATE_NEED_DELETE_RIGHT = (
    "Боту нужно право «Удалять сообщения» в группе обсуждений «{title}»."
)
COMMENTS_GATE_ENABLED = "Комментировать смогут только подписчики канала"
COMMENTS_GATE_DISABLED = "Подписка в комментариях выключена"

# --- manual subscription check (channel card) ---
BTN_CHAT_CHECK_USER = "🔍 Проверить подписчика"
CHECK_ASK_USER = (
    "🔍 <b>Проверка подписки на «{title}»</b>\n"
    f"{SEPARATOR}\n"
    "Пришлите <b>ID пользователя</b> числом или <b>перешлите</b> сюда его сообщение.\n"
    "Если у пользователя скрыта пересылка, подойдёт только ID.\n\n"
    "Можно присылать несколько подряд."
)
CHECK_BAD_INPUT = "Не понял. Нужен числовой ID или пересланное сообщение пользователя."
CHECK_SUBSCRIBED = "✅ <b>{name}</b> подписан на «{title}»\n" "Статус: {status}"
CHECK_NOT_SUBSCRIBED = "❌ <b>{name}</b> не подписан на «{title}»\n" "Статус: {status}"
CHECK_UNAVAILABLE = (
    "⚠️ Не удалось проверить: бот не администратор канала «{title}» "
    "или Telegram временно не отвечает."
)

# --- «награда за подписку» (channel card) ---
BTN_CHAT_REWARD = "🎁 Награда за подписку"
REWARD_CARD = (
    "🎁 <b>Награда за подписку на «{title}»</b>\n"
    f"{SEPARATOR}\n"
    "Пользователь переходит по ссылке, бот проверяет подписку и выдаёт награду. "
    "Не подписан — попросит подписаться и предложит «Проверить». "
    "Ваш собственный бот для этого не нужен.\n\n"
    "Награда: {status}\n"
    "Ссылка: <code>{link}</code>"
)
REWARD_STATUS_SET = "задана ✅ ({snippet})"
REWARD_STATUS_NONE = "не задана — нажмите «Задать награду»"
BTN_REWARD_SET = "✏️ Задать награду"
BTN_REWARD_SHOW = "👀 Показать награду"
BTN_REWARD_CLEAR = "🗑 Убрать награду"
BTN_REWARD_POST = "📣 Опубликовать кнопку в канал"
REWARD_ASK_CONTENT = (
    "✏️ <b>Награда</b>\n"
    f"{SEPARATOR}\n"
    "Пришлите сообщение, которое получит подписчик: текст (можно markdown), ссылку, "
    "фото, видео или файл с подписью."
)
REWARD_SAVED = "Награда сохранена"
REWARD_CLEARED = "Награда убрана"
REWARD_ASK_POST = (
    "📣 <b>Пост с кнопкой</b>\n"
    f"{SEPARATOR}\n"
    "Пришлите текст поста для канала «{title}». Под ним будет кнопка «{button}», "
    "ведущая на проверку подписки."
)
REWARD_POST_BUTTON = "🎁 Получить"
REWARD_POSTED = "Пост опубликован в канале"
REWARD_POST_FAILED = "Не удалось опубликовать: боту нужно право «Публиковать сообщения» в канале."
REWARD_NEED_CONTENT = "Сначала задайте награду"

# --- the subscriber's side (/start sub_…) ---
SUB_NEED_SUBSCRIPTION = (
    "🔒 <b>Подпишитесь на «{title}»</b>\n"
    f"{SEPARATOR}\n"
    "Чтобы получить материал, подпишитесь на канал и нажмите «Проверить»."
)
SUB_BTN_OPEN = "➕ Подписаться"
SUB_BTN_CHECK = "✅ Проверить"
SUB_OK = "✅ <b>Подписка подтверждена</b>\n" f"{SEPARATOR}\n" "Спасибо! Вот ваш материал 👇"
SUB_STILL_MISSING = "Подписка пока не найдена"
SUB_LINK_INVALID = "Ссылка устарела или награда больше не выдаётся."
SUB_UNAVAILABLE = "Не удалось проверить подписку: бот не администратор канала."
