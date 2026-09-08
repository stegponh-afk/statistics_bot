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
