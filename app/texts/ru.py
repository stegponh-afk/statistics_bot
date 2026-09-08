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
    "Что здесь есть:\n"
    "💬 <b>Чаты</b> — статистика ваших групп и каналов, обязательная подписка, "
    "проверка подписчиков, награда за подписку.\n"
    "🤖 <b>Боты</b> — подключить свой бот: проверка подписки и рассылки его пользователям.\n"
    "📨 <b>Рассылка</b> — отправить сообщение в чаты и ботам: сразу, по времени "
    "или по расписанию.\n\n"
    "Впервые здесь? Нажмите «Помощь» — там пошагово."
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
    "❓ <b>С чего начать</b>\n"
    f"{SEPARATOR}\n"
    "<b>Шаг 1. Подключите канал или группу</b>\n"
    "Откройте канал → Управление → Администраторы → Добавить администратора → "
    "найдите этого бота. Права можно не выдавать. Для группы то же самое, но "
    "включите право «Удалять сообщения».\n"
    "После этого чат сам появится в разделе «Чаты».\n\n"
    "<b>Шаг 2. Выберите, что нужно</b>\n"
    "📊 <b>Статистика</b> — «Чаты» → чат → «Статистика». В группе также команды "
    "/stats (для админов) и /me — ответ видите только вы.\n"
    "🔒 <b>Писать в группе только подписчикам канала</b> — «Чаты» → группа → "
    "«Каналы» → отметьте канал → «Обязательная подписка: ВКЛ».\n"
    "🎁 <b>Выдавать материал за подписку</b> — «Чаты» → канал → «Награда за подписку». "
    "Свой бот не нужен.\n"
    "🔍 <b>Проверить, подписан ли человек</b> — «Чаты» → канал → «Проверить подписчика».\n"
    "📨 <b>Рассылка</b> — раздел «Рассылка»: выбрать чаты, прислать сообщение, "
    "выбрать время.\n\n"
    "<b>Есть свой бот?</b> Раздел «Боты»: там ссылка для проверки подписки, которую "
    "можно вставить в конструктор бота, и рассылки его пользователям (нужен токен "
    "из @BotFather).\n\n"
    "Что-то не появляется — нажмите «Обновить» в «Чаты» или опубликуйте любое "
    "сообщение в чате."
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
    "💬 <b>Чаты</b>\n"
    f"{SEPARATOR}\n"
    "Пока пусто. Чтобы чат появился здесь:\n\n"
    "1. Откройте канал или группу → Управление → Администраторы.\n"
    "2. Нажмите «Добавить администратора» и выберите этого бота.\n"
    "3. Для группы включите право «Удалять сообщения», для канала права не нужны.\n\n"
    "Чат появится сам. Если бот уже добавлен, а чата нет — опубликуйте в нём любое "
    "сообщение или нажмите «Обновить»."
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
    "Здесь пока нет каналов, которые можно требовать. Чтобы канал появился:\n"
    "1. Откройте канал → Управление → Администраторы.\n"
    "2. Добавьте этого бота администратором (права не нужны).\n"
    "3. Вернитесь сюда и нажмите «Обновить».\n\n"
    "Без этого Telegram не позволяет боту видеть подписчиков канала."
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
    "Старый ключ больше не работает. Новый ключ:\n"
    "<code>{raw}</code>\n\n"
    "Готовая ссылка для проверки подписки:\n"
    "<code>{check_url}</code>"
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
    "📣 <b>Каналы бота «{name}»</b>\n"
    f"{SEPARATOR}\n"
    "Здесь пока нет каналов, подписку на которые можно проверять. Чтобы канал появился:\n"
    "1. Откройте канал → Управление → Администраторы.\n"
    "2. Добавьте этого бота администратором (права не нужны).\n"
    "3. Вернитесь сюда и нажмите «Обновить»."
)
KEY_HOWTO = (
    "📖 <b>Как проверять подписку в своём боте</b>\n"
    f"{SEPARATOR}\n"
    "Сначала для любого способа: добавьте этого бота администратором в ваши каналы, "
    "создайте бота в разделе «Боты» и отметьте в нём каналы («Каналы»).\n\n"
    "<b>Ваши готовые ссылки</b> (ключ и ваш ID <code>{user_id}</code> уже подставлены — "
    "откройте ссылку в браузере и увидите ответ):\n\n"
    "{links}\n\n"
    "<b>Способ 1 — без своего бота (проще всего)</b>\n"
    "«Чаты» → канал → «Награда за подписку». Задайте материал, получите ссылку или "
    "сразу опубликуйте пост с кнопкой. Этот бот сам проверит подписку и выдаст материал.\n\n"
    "<b>Способ 2 — бот на конструкторе</b> (PuzzleBot, BotHelp, SmartBotPro и похожие)\n"
    "В конструкторе добавьте действие «HTTP-запрос» (GET) со ссылкой «проверка» выше, "
    "только вместо вашего ID подставьте переменную с ID пользователя. В ответе будет поле "
    "<code>subscribed</code>: <code>true</code> — подписан, <code>false</code> — нет. "
    "Дальше обычное условие: подписан — показываем контент, нет — кнопки со ссылками "
    "из поля <code>missing</code>.\n\n"
    "<b>Способ 3 — свой код</b>\n"
    "Запрос с заголовком:\n"
    "<code>GET {base}/v1/check?user_id=ID</code>\n"
    "<code>Authorization: Bearer ВАШ_КЛЮЧ</code>\n"
    "Ответ:\n"
    '<code>{{"ok": true, "subscribed": false, "missing": [{{"chat_id": -100…, '
    '"title": "Канал", "invite_link": "https://t.me/…"}}]}}</code>\n'
    "Ответ кэшируется около минуты, <code>&force=1</code> проверяет заново "
    "(например, по кнопке «Проверить»). Лимит: {limit} запросов в минуту на ключ."
)
KEY_LINKS_BLOCK = (
    "<b>Бот «{name}»</b>\n"
    "Проверка подписки:\n"
    "<code>{check_url}</code>\n"
    "Список каналов:\n"
    "<code>{channels_url}</code>"
)
KEY_LINKS_BLOCK_NO_RAW = (
    "<b>Бот «{name}»</b>\n"
    "Ключ выпущен до обновления — нажмите «Перевыпустить» в карточке бота, "
    "и ссылки появятся здесь."
)
KEY_LINKS_NONE = "<i>Пока нет ботов — создайте бота в разделе «Боты», и ссылки появятся здесь.</i>"

# --- bots (the owner's own bots: API key + token + audience) ---
BTN_MY_BOTS = "🤖 Боты"
BTN_BROADCAST = "📨 Рассылка"
BOTS_TITLE = (
    "🤖 <b>Боты</b>\n"
    f"{SEPARATOR}\n"
    "Здесь подключаются ваши собственные боты. Для каждого можно:\n"
    "· проверять, подписан ли его пользователь на ваши каналы (по ссылке или API);\n"
    "· делать рассылки его пользователям от его имени (нужен токен из @BotFather).\n\n"
    "Нет своего бота? Тогда вам сюда не нужно: награда за подписку и проверка "
    "подписчиков работают через этот бот, см. «Чаты»."
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
    "Ваш API-ключ:\n"
    "<code>{raw}</code>\n\n"
    "Готовая ссылка для проверки подписки — уже с вашим ключом и вашим ID, "
    "откройте её в браузере и увидите ответ:\n"
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
    "Аудитория для рассылок: <b>{audience}</b>{blocked_line}\n\n"
    "Готовая ссылка для проверки подписки (с вашим ключом и вашим ID — можно "
    "открыть в браузере и посмотреть ответ):\n"
    "<code>{check_url}</code>"
)
KEY_RAW_MISSING = "нажмите «Перевыпустить», чтобы получить ссылку"
BOT_TOKEN_SET = "добавлен (@{username})"
BOT_TOKEN_MISSING = "не добавлен — рассылки недоступны"
BOT_BLOCKED_LINE = " (заблокировали бота: {blocked})"
BTN_BOT_TOKEN_ADD = "🔐 Добавить токен"
BTN_BOT_TOKEN_REMOVE = "🔐 Убрать токен"
BOT_ASK_TOKEN = (
    "🔐 <b>Токен бота</b>\n"
    f"{SEPARATOR}\n"
    "Токен — это «пароль» вашего бота, с ним мы сможем отправлять рассылки от его имени.\n\n"
    "Где взять:\n"
    "1. Откройте @BotFather в Telegram.\n"
    "2. Отправьте /mybots и выберите вашего бота.\n"
    "3. Нажмите «API Token» и скопируйте строку вида <code>123456789:AAE…</code>.\n"
    "4. Пришлите её сюда одним сообщением.\n\n"
    "Токен хранится в базе этого сервиса — добавляйте, только если доверяете ему. "
    "Ваше сообщение с токеном будет удалено из чата."
)
BOT_TOKEN_INVALID = "Токен не подошёл: Telegram его не принял. Проверьте и пришлите ещё раз."
BOT_TOKEN_SAVED = "Токен сохранён: @{username}"
BOT_TOKEN_REMOVED = "Токен удалён"
BOT_AUDIENCE_HINT = (
    "Аудитория — пользователи вашего бота, которых он проверял через "
    "<code>/v1/check</code> или зарегистрировал через <code>POST /v1/users</code>."
)
KEY_HOWTO_USERS = (
    "\n\n<b>Рассылки пользователям вашего бота</b>\n"
    "Добавьте токен бота (кнопка «Добавить токен»). Все, кого ваш бот проверял по "
    "ссылке выше, автоматически попадают в аудиторию. Остальных можно добавить запросом:\n"
    "<code>POST {base}/v1/users</code>\n"
    '<code>{{"user_ids": [1, 2, 3]}}</code>\n'
    "(до 10 000 за раз). Затем раздел «Рассылка» → выбрать бота."
)

# --- broadcasts ---
BROADCAST_MENU = (
    "📨 <b>Рассылка</b>\n"
    f"{SEPARATOR}\n"
    "Как это работает:\n"
    "1. «Новая рассылка» → отметьте чаты и ботов, куда отправить.\n"
    "2. Пришлите сообщение: текст, фото, видео или файл с подписью.\n"
    "3. При желании добавьте кнопки-ссылки.\n"
    "4. Выберите: отправить сейчас, к определённому времени или по расписанию.\n\n"
    "В «Мои рассылки» — статус, счётчики доставки, пауза и удаление."
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
    "Как это работает: человек нажимает вашу ссылку или кнопку, попадает в этого бота, "
    "бот проверяет подписку на канал и выдаёт награду. Если не подписан — попросит "
    "подписаться и нажать «Проверить». Каждый получает награду один раз.\n\n"
    "Что сделать:\n"
    "1. «Задать награду» — пришлите материал для подписчиков.\n"
    "2. Разместите ссылку ниже где угодно или нажмите «Опубликовать кнопку в канал».\n\n"
    "Награда: {status}\n"
    "Получили: <b>{claims}</b> чел.\n"
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
SUB_ALREADY = (
    "🎁 <b>Награда уже получена</b>\n"
    f"{SEPARATOR}\n"
    "Вы уже получали этот материал {when}. Повторно он не выдаётся."
)
BTN_REWARD_RESET = "♻️ Сбросить выдачи"
REWARD_RESET_DONE = "Список получивших очищен — награду смогут получить снова"
SUB_STILL_MISSING = "Подписка пока не найдена"
SUB_LINK_INVALID = "Ссылка устарела или награда больше не выдаётся."
SUB_UNAVAILABLE = "Не удалось проверить подписку: бот не администратор канала."

# --- «Чаты» hub ---
MY_CHATS_HUB = (
    "💬 <b>Чаты</b>\n"
    f"{SEPARATOR}\n"
    "Каналов: <b>{channels}</b> · групп: <b>{groups}</b>\n"
    "Выберите, что открыть:"
)
BTN_CHATS_CHANNELS = "📣 Каналы ({count})"
BTN_CHATS_GROUPS = "👥 Группы ({count})"
MY_CHANNELS_TITLE = "📣 <b>Каналы</b>"
MY_GROUPS_TITLE = "👥 <b>Группы</b>"
MY_CHANNELS_EMPTY = (
    "Пока ни одного канала. Добавьте этого бота администратором канала "
    "(Управление → Администраторы → Добавить), права не нужны."
)
MY_GROUPS_EMPTY = (
    "Пока ни одной группы. Добавьте этого бота в группу и назначьте администратором "
    "с правом «Удалять сообщения»."
)

# --- channel statistics ---
STATS_MEMBERS_FLOW_LINE = "Участников: <b>{count}</b> (сегодня +{joins} / −{leaves})\n"
STATS_CHANNEL_OVERVIEW = (
    "📣 <b>Статистика: {title}</b>\n"
    f"{SEPARATOR}\n"
    "<b>Подписчики</b>\n"
    "Сейчас: <b>{members}</b>\n"
    "Сегодня: +{today_joins} / −{today_leaves} (<b>{today_net}</b>)\n"
    "Вчера: +{yday_joins} / −{yday_leaves} (<b>{yday_net}</b>)\n"
    "За 7 дней: <b>{week}</b> · за 30 дней: <b>{month}</b>\n\n"
    "<b>Посты</b>\n"
    "Сегодня: <b>{posts_today}</b> · за 7 дней: <b>{posts_week}</b> · "
    "за 30 дней: <b>{posts_month}</b>\n"
    "Реакций на пост в среднем (30 дней): <b>{avg_reactions}</b>\n"
    "Лучший пост: {best}\n"
    "{comments_line}"
    "\n<i>Просмотры постов Telegram ботам не отдаёт. Приток/отток считается с момента "
    "добавления бота, история подписчиков копится по дням. Часовой пояс: {tz}</i>"
)
STATS_BEST_POST = "<b>{total}</b> реакций — {link}"
STATS_COMMENTS_LINE = "Комментариев за 7 дней: <b>{count}</b>\n"
BTN_STATS_DYNAMICS = "📈 Динамика"
BTN_STATS_POSTS = "🔥 Посты"
STATS_DYNAMICS_TITLE = "📈 <b>Последние 14 дней</b>"
STATS_DYNAMICS_HEADER = "<code>дата   подписч.  +/−      постов</code>"
STATS_DYNAMICS_ROW = "<code>{day}  {subscribers:>8}  +{joins}/−{leaves}  {posts}</code>"
STATS_TOP_POSTS_TITLE = "🔥 <b>Посты по реакциям за 30 дней</b>"
STATS_TOP_POSTS_EMPTY = (
    "Пока нет данных. Реакции считаются по постам, опубликованным после добавления бота, "
    "и приходят от Telegram с задержкой в несколько минут."
)
STATS_TOP_POST_ROW = "{n}. <b>{total}</b> реакций · {day} · {link}"
