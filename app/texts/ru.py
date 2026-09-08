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
    "здесь автоматически. Если бот уже добавлен, нажмите «Обновить»."
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
