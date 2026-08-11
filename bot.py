"""Telegram Business translator with a private management panel."""

import asyncio
import logging
import io
import os
import re
import secrets
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    KeyboardButtonRequestUsers,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ChatAction
from telegram.error import BadRequest, Forbidden, TimedOut
from telegram.ext import (
    Application,
    BusinessConnectionHandler,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()
logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN: Final = os.getenv("TELEGRAM_BOT_TOKEN", "")
# Text translation prioritizes meaning and multilingual quality over the lowest cost.
MODEL: Final = os.getenv("TRANSLATION_MODEL", "gpt-5.6-sol")
TRANSCRIBE_MODEL: Final = os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")
DB_PATH: Final = Path(os.getenv("DATABASE_PATH", str(Path(__file__).with_name("translator.sqlite3"))))
BOOTSTRAP_ADMIN_IDS: Final = tuple(
    int(value) for value in os.getenv("BOOTSTRAP_ADMIN_IDS", "").split(",") if value.strip().isdigit()
)
# The connection can be slow on some networks; do not fail a translation after
# the short default connection timeout.
client = AsyncOpenAI(
    timeout=httpx.Timeout(90.0, connect=30.0, read=90.0, write=30.0, pool=30.0),
    max_retries=3,
)

LANGUAGES = {
    "ru": "Русский",
    "en": "English",
    "es": "Español",
    "de": "Deutsch",
    "tk": "Türkmençe (туркменский)",
    "tg": "Тоҷикӣ (таджикский)",
    "ky": "Кыргызча (кыргызский)",
    "uz": "O‘zbekcha (lotin)",
    "uz_cyr": "Ўзбекча (кирилл)",
}
TONES = {
    "formal": "Официально",
    "casual": "Обычный чат",
    "brief": "Коротко и по делу",
}
TEMPLATES = {
    "hello": "Здравствуйте! Спасибо за сообщение. Чем я могу помочь?",
    "wait": "Спасибо! Я уточню информацию и скоро отвечу.",
    "price": "Спасибо за интерес. Пожалуйста, уточните, какой вариант вас интересует.",
    "bye": "Спасибо за обращение! Хорошего дня.",
}
SELECT_ADMIN_REQUEST: Final = 8101
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [["⚙️ Панель управления", "📝 Холодное сообщение"], ["🌐 Перевести текст", "🎙 Перевести голос"], ["ℹ️ Как пользоваться", "❌ Отмена"]],
    resize_keyboard=True,
)

# Keep the chat clean: the only regular interaction is choosing a language.
MAIN_KEYBOARD = ReplyKeyboardRemove()

# One entry point for both incoming-text translation and composing a message.
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [["⚙️ Панель управления", "🌐 Перевести текст"], ["🎙 Перевести голос", "ℹ️ Как пользоваться"], ["❌ Отмена"]],
    resize_keyboard=True,
)

# Final keyboard configuration for production: no bottom menu.
MAIN_KEYBOARD = ReplyKeyboardRemove()


@dataclass(frozen=True)
class PendingReply:
    connection_id: str
    customer_chat_id: int
    language: str
    customer_name: str
    owner_id: int


# Draft replies are valid only while this process is running. Account settings,
# connections and statistics are stored permanently in SQLite.
pending_replies: dict[str, PendingReply] = {}
conversation_choices: dict[str, PendingReply] = {}
TURKMEN_RUSSIAN_PHRASES: Final = {
    "bolya": "Хорошо.",
    "bolýa": "Хорошо.",
    "düşünmedim näme diýjekdiňiz": "Я не понял, что вы хотели сказать?",
    "dusunmedim name diyjekdiniz": "Я не понял, что вы хотели сказать?",
    "na jigim oynamana adam tapanokmy": "Ну, брат, не можешь найти игроков?",
    "men sende bu zatlary melbetde acsam hem edip bilyan dogrumy": (
        "Если я открою это у тебя в MelBet, я тоже смогу так делать, правильно?"
    ),
}


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
              user_id INTEGER PRIMARY KEY,
              incoming_language TEXT NOT NULL DEFAULT 'ru',
              tone TEXT NOT NULL DEFAULT 'casual',
              enabled INTEGER NOT NULL DEFAULT 1,
              incoming_count INTEGER NOT NULL DEFAULT 0,
              outgoing_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS business_accounts (
              connection_id TEXT PRIMARY KEY,
              owner_id INTEGER NOT NULL,
              owner_inbox_id INTEGER NOT NULL,
              connected INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS admins (
              user_id INTEGER PRIMARY KEY,
              display_name TEXT NOT NULL DEFAULT '',
              added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS clients (
              owner_id INTEGER NOT NULL,
              connection_id TEXT NOT NULL,
              chat_id INTEGER NOT NULL,
              name TEXT NOT NULL,
              language TEXT NOT NULL,
              last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (owner_id, connection_id, chat_id)
            );
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO admins (user_id) "
            "SELECT owner_id FROM business_accounts WHERE connected = 1"
        )
        for user_id in BOOTSTRAP_ADMIN_IDS:
            conn.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
        columns = {row[1] for row in conn.execute("PRAGMA table_info(admins)")}
        if "display_name" not in columns:
            conn.execute("ALTER TABLE admins ADD COLUMN display_name TEXT NOT NULL DEFAULT ''")
        conn.execute("UPDATE user_settings SET tone = 'casual' WHERE tone = 'clear'")


def ensure_user(user_id: int) -> None:
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,))


def add_admin(user_id: int, display_name: str = "") -> None:
    with db() as conn:
        conn.execute(
            """INSERT INTO admins (user_id, display_name) VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET display_name =
               CASE WHEN excluded.display_name != '' THEN excluded.display_name ELSE admins.display_name END""",
            (user_id, display_name),
        )


def all_admins() -> list[sqlite3.Row]:
    with db() as conn:
        return conn.execute("SELECT user_id, display_name FROM admins ORDER BY added_at").fetchall()


def is_business_owner(user_id: int) -> bool:
    with db() as conn:
        return conn.execute(
            "SELECT 1 FROM business_accounts WHERE owner_id = ? AND connected = 1", (user_id,)
        ).fetchone() is not None


def remove_admin(user_id: int) -> None:
    with db() as conn:
        conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))


def set_admin_name(user_id: int, display_name: str) -> None:
    with db() as conn:
        conn.execute("UPDATE admins SET display_name = ? WHERE user_id = ?", (display_name, user_id))


def is_admin(user_id: int) -> bool:
    with db() as conn:
        return conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)).fetchone() is not None


async def require_admin(update: Update) -> bool:
    user = update.effective_user
    if user and is_admin(user.id):
        return True
    message = update.effective_message
    if message:
        await message.reply_text("⛔ Доступ закрыт. Бот доступен только подключённым Business-администраторам.")
    return False


def settings(user_id: int) -> sqlite3.Row:
    ensure_user(user_id)
    with db() as conn:
        return conn.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,)).fetchone()


def set_setting(user_id: int, field: str, value: object) -> None:
    if field not in {"incoming_language", "tone", "enabled"}:
        raise ValueError("Unsupported setting")
    ensure_user(user_id)
    with db() as conn:
        conn.execute(f"UPDATE user_settings SET {field} = ? WHERE user_id = ?", (value, user_id))


def increment(user_id: int, field: str) -> None:
    if field not in {"incoming_count", "outgoing_count"}:
        raise ValueError("Unsupported counter")
    ensure_user(user_id)
    with db() as conn:
        conn.execute(f"UPDATE user_settings SET {field} = {field} + 1 WHERE user_id = ?", (user_id,))


def save_business_account(connection_id: str, owner_id: int, inbox_id: int, connected: bool) -> None:
    ensure_user(owner_id)
    if connected:
        add_admin(owner_id)
    with db() as conn:
        conn.execute(
            """INSERT INTO business_accounts (connection_id, owner_id, owner_inbox_id, connected)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(connection_id) DO UPDATE SET owner_id=excluded.owner_id,
               owner_inbox_id=excluded.owner_inbox_id, connected=excluded.connected""",
            (connection_id, owner_id, inbox_id, int(connected)),
        )


def stored_business_account(connection_id: str) -> tuple[int, int] | None:
    with db() as conn:
        row = conn.execute(
            "SELECT owner_id, owner_inbox_id FROM business_accounts WHERE connection_id = ? AND connected = 1",
            (connection_id,),
        ).fetchone()
    return (row["owner_id"], row["owner_inbox_id"]) if row else None


def save_client(owner_id: int, connection_id: str, chat_id: int, name: str, language: str) -> None:
    with db() as conn:
        conn.execute(
            """INSERT INTO clients (owner_id, connection_id, chat_id, name, language)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(owner_id, connection_id, chat_id) DO UPDATE SET
               name=excluded.name, language=excluded.language, last_seen=CURRENT_TIMESTAMP""",
            (owner_id, connection_id, chat_id, name, language),
        )


def stored_client_language(owner_id: int, connection_id: str, chat_id: int) -> str:
    with db() as conn:
        row = conn.execute(
            "SELECT language FROM clients WHERE owner_id = ? AND connection_id = ? AND chat_id = ?",
            (owner_id, connection_id, chat_id),
        ).fetchone()
    return row["language"] if row and row["language"] not in {"", "Unknown"} else ""


def recent_clients(owner_id: int) -> list[sqlite3.Row]:
    with db() as conn:
        return conn.execute(
            "SELECT connection_id, chat_id, name, language FROM clients WHERE owner_id = ? "
            "ORDER BY last_seen DESC LIMIT 12", (owner_id,)
        ).fetchall()


def set_client_language(owner_id: int, connection_id: str, chat_id: int, language: str) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE clients SET language = ? WHERE owner_id = ? AND connection_id = ? AND chat_id = ?",
            (language, owner_id, connection_id, chat_id),
        )


def translation_instruction(target: str, tone: str = "clear") -> str:
    language_note = ""
    if target.startswith("Тоҷикӣ"):
        language_note = (
            " For Tajik, use modern everyday Tajik written in Cyrillic, with familiar local wording; "
            "do not substitute Persian literary forms."
        )
    elif target.startswith("Türkmençe"):
        language_note = (
            " For Turkmen, use modern everyday Turkmen written in its standard Latin alphabet. "
            "Use natural Turkmen chat wording, not Turkish substitutions or literary phrasing."
        )
    tone_text = {
        "brief": (
            "Use a compact everyday chat style. Prefer a short phrase of roughly 3 to 12 words for "
            "a simple update, and no more than two short sentences when details are necessary. Keep one "
            "idea per message."
        ),
        "casual": (
            "Use a relaxed, friendly regional chat style. Prefer one or two short natural sentences "
            "instead of a long paragraph. Keep one idea or request per message. Use simple greetings "
            "and direct everyday questions when they are present in the source. Keep the wording familiar "
            "and natural for the target language. Preserve the emoji level of the source: do not add emojis "
            "when the source has none. Do not polish casual messages into textbook grammar or literary wording. "
            "Use common chat shortcuts and everyday variants only when they are widely understood in the target "
            "language. Do not invent slang, intentional mistakes, imitate a specific person, or use pressure tactics."
        ),
        "formal": "Use polite, formal business wording.",
    }.get(tone, "Use simple, clear everyday wording.")
    return (
        f"You are a careful translator. Return only a natural translation into {target}. "
        "Make it sound like a real local person writing a normal chat message to a friend or "
        "colleague, never like a translation engine, AI assistant, textbook, or official template. "
        "Translate the meaning, not word by word. Prefer short, familiar everyday words and natural "
        "sentence structure. Avoid literary vocabulary, bureaucratic phrases, stiff politeness, and "
        "long complicated sentences unless the selected tone explicitly requires formality. Understand "
        "that the source can be colloquial Turkmen typed in Latin without diacritics and with spellings "
        "that resemble Turkish. Treat words such as 'men', 'sende', 'zat', 'hem', 'bilyan', and 'dogrumy' "
        "as Turkmen chat wording, not Turkish; translate their intended meaning in context. In this chat "
        "style, 'jigim' is often a friendly address like 'bro' or 'buddy', not a romantic female address. "
        "common chat abbreviations, slang, missing words, and obvious typos; expand or rephrase them "
        "naturally only when their meaning is clear. Never invent facts or change the intent. Do not "
        "add labels, greetings, quotes, explanations, or notes unless they exist in the source. Preserve names, numbers, links and "
        "emojis. Correct only mistakes that make the meaning unclear; do not over-correct a casual message into "
        f"formal or literary language. {tone_text}{language_note}"
    )


async def translate_text(text: str, target: str, tone: str = "clear") -> str:
    normalized = " ".join(text.casefold().strip(" .,!?:;…").split())
    if target == "Русский" and normalized in TURKMEN_RUSSIAN_PHRASES:
        return TURKMEN_RUSSIAN_PHRASES[normalized]
    response = await client.responses.create(
        model=MODEL, instructions=translation_instruction(target, tone), input=text
    )
    result = response.output_text.strip()
    if not result:
        raise RuntimeError("The model returned an empty translation")
    latin_targets = ("English", "Español", "Deutsch", "Türkmençe", "O‘zbekcha")
    cyrillic = sum("А" <= char <= "я" or char in "ЁёЎўҚқҒғҲҳҶҷӢӣ" for char in result)
    if target.startswith(latin_targets) and cyrillic >= 3:
        retry = await client.responses.create(
            model=MODEL,
            instructions=(
                translation_instruction(target, tone)
                + f" CRITICAL: Return the translation only in {target}. The previous result was in Cyrillic "
                "and was wrong. Use the target language's Latin alphabet, not Russian."
            ),
            input=text,
        )
        corrected = retry.output_text.strip()
        if corrected:
            result = corrected
    return result


async def translate_incoming(text: str, target: str, known_language: str = "") -> tuple[str, str]:
    """Detect language and translate in one model request to minimize latency."""
    normalized = text.casefold().strip(" .,!?:;…")
    if target == "Русский" and normalized in TURKMEN_RUSSIAN_PHRASES:
        return "Turkmen", TURKMEN_RUSSIAN_PHRASES[normalized]
    hint = f" The sender's previous messages were in {known_language}; use that as a strong hint." if known_language else ""
    response = await client.responses.create(
        model=MODEL,
        instructions=(
            "Detect the message language and translate it. Output exactly two parts: "
            "the first line is only the common English language name (for example, "
            "English, Turkmen, Uzbek); every following line is a short, simple, everyday translation "
            f"into {target} that sounds like a real person, not a translation tool. Translate meaning rather than word-for-word. Understand common chat "
            "abbreviations, slang, omitted words, and obvious typos when their meaning is clear; "
            "recognize colloquial Turkmen written in Latin without diacritics, even when it resembles Turkish; "
            "do not invent information. Very short chat words must still receive the most likely practical "
            "translation; do not answer that a word is unknown or ask a question. Do not add any labels or explanations."
            f"{hint}"
        ),
        input=text,
    )
    language, separator, translated = response.output_text.strip().partition("\n")
    if not separator or not translated.strip():
        raise RuntimeError("The model returned an invalid translation format")
    if not re.fullmatch(r"[A-Za-z][A-Za-z -]{0,38}", language.strip()):
        language = "English"
    if language.strip().lower() in {"unknown", "undetermined", "unrecognized"} and known_language:
        language = known_language
    return language.strip(), translated.strip()


def panel_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🌐 Язык входящих", callback_data="panel:language"), InlineKeyboardButton("✨ Стиль ответа", callback_data="panel:tone")],
            [InlineKeyboardButton("💬 Быстрые ответы", callback_data="panel:templates"), InlineKeyboardButton("📊 Статистика", callback_data="panel:stats")],
            [InlineKeyboardButton("💬 Начать беседу", callback_data="panel:conversations")],
            [InlineKeyboardButton("🌐 Перевести текст", callback_data="panel:translate")],
            [InlineKeyboardButton("👤 Добавить администратора", callback_data="panel:addadmin"), InlineKeyboardButton("👥 Администраторы", callback_data="panel:admins")],
            [InlineKeyboardButton("⏸ Вкл./выкл. перевод", callback_data="panel:toggle")],
        ]
    )


def panel_text(user_id: int) -> str:
    row = settings(user_id)
    status = "включён" if row["enabled"] else "поставлен на паузу"
    return (
        "⚙️ Панель управления\n\n"
        f"Перевод входящих: {LANGUAGES.get(row['incoming_language'], 'Русский')}\n"
        f"Стиль ответов: {TONES.get(row['tone'], 'Понятно')}\n"
        f"Автоперевод: {status}\n\n"
        "Выберите действие ниже."
    )


def cold_language_markup() -> InlineKeyboardMarkup:
    items = list(LANGUAGES.items())
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"coldtextlang:{key}") for key, label in items[i:i + 2]]
        for i in range(0, len(items), 2)
    ]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="panel:home")])
    return InlineKeyboardMarkup(buttons)


def cold_start_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔎 Указать @username или ссылку", callback_data="coldtarget")],
            [InlineKeyboardButton("📝 Только подготовить перевод", callback_data="coldplain")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="panel:home")],
        ]
    )


def translate_start_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📩 Мне прислали текст", callback_data="translate:incoming")],
            [InlineKeyboardButton("✍️ Я хочу написать клиенту", callback_data="translate:outgoing")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="panel:home")],
        ]
    )


async def show_translate_start(message, edit: bool = False) -> None:
    if edit:
        await message.edit_text("Что хотите перевести?", reply_markup=translate_start_markup())
    else:
        await message.reply_text("Что хотите перевести?", reply_markup=translate_start_markup())


def parse_telegram_target(value: str) -> str | None:
    """Return a safe public Telegram link from a username or t.me link."""
    value = value.strip().rstrip("/")
    match = re.fullmatch(r"@?([A-Za-z][A-Za-z0-9_]{4,31})", value)
    if not match:
        match = re.fullmatch(r"(?:https?://)?t\.me/([A-Za-z][A-Za-z0-9_]{4,31})", value, re.IGNORECASE)
    return f"https://t.me/{match.group(1)}" if match else None


async def show_cold_start(message, edit: bool = False) -> None:
    text = (
        "🔎 Холодное сообщение\n\n"
        "Укажите @username или ссылку на публичный Telegram-аккаунт — после перевода я дам кнопку "
        "для быстрого открытия его чата. Либо подготовьте перевод без выбора человека."
    )
    if edit:
        await message.edit_text(text, reply_markup=cold_start_markup())
    else:
        await message.reply_text(text, reply_markup=cold_start_markup())


async def show_cold_picker(message, edit: bool = False) -> None:
    text = "Выберите язык клиента. Затем напишите сообщение по-русски — я переведу его."
    if edit:
        await message.edit_text(text, reply_markup=cold_language_markup())
    else:
        await message.reply_text(text, reply_markup=cold_language_markup())


async def show_panel(message, user_id: int, edit: bool = False) -> None:
    if edit:
        await message.edit_text(panel_text(user_id), reply_markup=panel_markup())
    else:
        await message.reply_text(panel_text(user_id), reply_markup=panel_markup())


async def show_admins(message, edit: bool = False) -> None:
    rows = all_admins()
    lines = ["👥 Администраторы\n"]
    buttons = []
    for row in rows:
        label = row["display_name"]
        if not label:
            try:
                chat = await message.get_bot().get_chat(row["user_id"])
                label = getattr(chat, "full_name", "") or chat.username or ""
                if label:
                    set_admin_name(row["user_id"], label)
            except Exception:
                pass
        label = label or f"Аккаунт {row['user_id']}"
        if is_business_owner(row["user_id"]):
            lines.append(f"🔒 {label} — владелец Business")
        else:
            lines.append(f"👤 {label}")
            buttons.append([InlineKeyboardButton(f"🗑 Удалить: {label[:30]}", callback_data=f"adminrm:{row['user_id']}")])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="panel:home")])
    text = "\n".join(lines)
    markup = InlineKeyboardMarkup(buttons)
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.reply_text(text, reply_markup=markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update):
        return
    await update.effective_message.reply_text(
        "Здравствуйте! Я ваш личный переводчик для Telegram Business.\n\n"
        "Сообщения клиентов перевожу сюда, а ваш ответ по-русски отправляю клиенту на его языке.\n"
        "Кнопки управления находятся под полем ввода."
        , reply_markup=MAIN_KEYBOARD
    )
    await show_panel(update.effective_message, update.effective_user.id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Minimal workflow: choose a destination language, then type in Russian."""
    if not await require_admin(update):
        return
    clear_reply_flow(context)
    await update.effective_message.reply_text(
        "Выберите язык перевода. Затем просто пишите сообщения по-русски — я переведу их.",
        reply_markup=MAIN_KEYBOARD,
    )
    await show_cold_picker(update.effective_message)


async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update):
        return
    await show_panel(update.effective_message, update.effective_user.id)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update):
        return
    context.user_data.pop("pending_reply", None)
    await update.effective_message.reply_text("Подготовка ответа отменена.")


def clear_reply_flow(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop any active client conversation before starting a separate task."""
    for key in (
        "pending_reply",
        "active_conversation",
        "cold_draft_language",
        "cold_target_url",
        "waiting_cold_target",
        "manual_translate",
        "manual_voice_translate",
    ):
        context.user_data.pop(key, None)


def clear_cold_flow(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove draft-only states before replying to a real client."""
    for key in ("cold_draft_language", "cold_target_url", "waiting_cold_target", "manual_translate", "manual_voice_translate"):
        context.user_data.pop(key, None)


async def cold(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update):
        return
    clear_reply_flow(context)
    await show_cold_start(update.effective_message)


async def remember_business_connection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    connection = update.business_connection
    if connection:
        save_business_account(connection.id, connection.user.id, connection.user_chat_id, connection.is_enabled)
        logger.info("Business connection %s updated", connection.id)


async def get_business_account(connection_id: str, context: ContextTypes.DEFAULT_TYPE) -> tuple[int, int]:
    account = stored_business_account(connection_id)
    if account:
        return account
    connection = await context.bot.get_business_connection(connection_id)
    account = (connection.user.id, connection.user_chat_id)
    save_business_account(connection.id, *account, connection.is_enabled)
    return account


async def receive_business_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.business_message
    if not message or not message.text or message.sender_business_bot or not message.business_connection_id:
        return
    try:
        owner_id, inbox_id = await get_business_account(message.business_connection_id, context)
        if message.from_user and message.from_user.id == owner_id:
            return
        owner_settings = settings(owner_id)
        if not owner_settings["enabled"]:
            return
        target = LANGUAGES.get(owner_settings["incoming_language"], "Русский")
        known_language = stored_client_language(owner_id, message.business_connection_id, message.chat_id)
        source, translated = await translate_incoming(message.text, target, known_language)
        token = secrets.token_urlsafe(18)
        sender = message.from_user.full_name if message.from_user else "Клиент"
        save_client(owner_id, message.business_connection_id, message.chat_id, sender, source)
        pending_replies[token] = PendingReply(message.business_connection_id, message.chat_id, source, sender, owner_id)
        buttons = [[InlineKeyboardButton("✍️ Ответить по-русски", callback_data=f"reply:{token}")]]
        buttons.append([
            InlineKeyboardButton("👋 Приветствие", callback_data=f"quick:{token}:hello"),
            InlineKeyboardButton("⏳ Уточню", callback_data=f"quick:{token}:wait"),
        ])
        buttons.append([
            InlineKeyboardButton("📋 Нужны детали", callback_data=f"quick:{token}:price"),
            InlineKeyboardButton("🙏 Спасибо", callback_data=f"quick:{token}:bye"),
        ])
        buttons.append([InlineKeyboardButton("🌐 Изменить язык", callback_data=f"replang:{token}")])
        if message.from_user:
            buttons.append(
                [InlineKeyboardButton("💬 Открыть чат с клиентом", url=f"tg://user?id={message.from_user.id}")]
            )
        buttons.append([InlineKeyboardButton("⚙️ Панель", callback_data="panel:home")])
        keyboard = InlineKeyboardMarkup(buttons)
        await context.bot.send_message(
            chat_id=inbox_id,
            text=f"📩 От: {sender}\nЯзык: {source}\n\n{translated}",
            reply_markup=keyboard,
        )
        increment(owner_id, "incoming_count")
    except Exception:
        logger.exception("Could not process business message")


def business_send_error_text(error: Exception) -> str:
    details = str(error).upper()
    if "BUSINESS_PEER_USAGE_MISSING" in details or "PEER_USAGE" in details:
        return (
            "Telegram не разрешил отправку: клиент должен написать вам в личный чат недавно. "
            "Попросите его отправить новое сообщение, затем ответьте через бота."
        )
    if "BUSINESS_CONNECTION" in details or "FORBIDDEN" in details:
        return (
            "Telegram не разрешил отправку в этот чат. Проверьте в Telegram Business → Чат-боты, "
            "что для бота включено «Отвечать на сообщения» и этот чат входит в разрешённые."
        )
    return (
        "Не удалось отправить сообщение. Причина Telegram: "
        f"{str(error)[:180]}\n\nПопробуйте после нового сообщения клиента."
    )


async def send_business_text(context: ContextTypes.DEFAULT_TYPE, recipient: PendingReply, text: str) -> None:
    """Send through Telegram Business and retry one temporary timeout."""
    for attempt in range(2):
        try:
            await context.bot.send_message(
                chat_id=recipient.customer_chat_id,
                text=text,
                business_connection_id=recipient.connection_id,
                connect_timeout=15,
                write_timeout=30,
                read_timeout=30,
                pool_timeout=30,
            )
            return
        except TimedOut:
            if attempt:
                raise
            logger.warning("Telegram timed out while sending; retrying once")
            await asyncio.sleep(2)


async def send_pending_reply(message, context: ContextTypes.DEFAULT_TYPE, russian_text: str) -> None:
    token = context.user_data.get("pending_reply")
    pending = pending_replies.get(token) if token else None
    if not pending:
        await message.reply_text("Сначала нажмите «Ответить по-русски» под сообщением клиента.")
        return
    try:
        tone = settings(pending.owner_id)["tone"]
        await message.chat.send_action(ChatAction.TYPING)
        translated = await translate_text(russian_text, pending.language, tone)
        await send_business_text(context, pending, translated)
        increment(pending.owner_id, "outgoing_count")
        context.user_data.pop("pending_reply", None)
        context.user_data["active_conversation"] = pending
        await message.reply_text(
            f"✅ Отправлено ({pending.language}):\n\n{translated}\n\n"
            f"💬 Беседа с «{pending.customer_name}» закреплена. Следующие сообщения будут отправляться только ему. "
            "Чтобы сменить человека, нажмите «❌ Отмена».",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("💬 Открыть чат с клиентом", url=f"tg://user?id={pending.customer_chat_id}")]]
            ),
        )
    except (BadRequest, Forbidden) as error:
        logger.exception("Could not send business reply")
        await message.reply_text(business_send_error_text(error))
    except Exception as error:
        logger.exception("Could not send business reply")
        await message.reply_text(business_send_error_text(error))


async def send_active_message(message, context: ContextTypes.DEFAULT_TYPE, russian_text: str) -> None:
    active = context.user_data.get("active_conversation")
    if not isinstance(active, PendingReply):
        context.user_data.pop("active_conversation", None)
        await message.reply_text("Эта беседа больше недоступна. Откройте «Начать беседу» ещё раз.")
        return
    try:
        tone = settings(active.owner_id)["tone"]
        await message.chat.send_action(ChatAction.TYPING)
        translated = await translate_text(russian_text, active.language, tone)
        await send_business_text(context, active, translated)
        increment(active.owner_id, "outgoing_count")
        await message.reply_text(
            f"✅ Отправлено «{active.customer_name}» ({active.language}).",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("💬 Открыть чат с клиентом", url=f"tg://user?id={active.customer_chat_id}")]]
            ),
        )
    except (BadRequest, Forbidden) as error:
        logger.exception("Could not send active conversation message")
        await message.reply_text(business_send_error_text(error))
    except Exception as error:
        logger.exception("Could not send active conversation message")
        await message.reply_text(business_send_error_text(error))


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data or ""
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.answer("Доступ закрыт.", show_alert=True)
        return
    if data.startswith("reply:"):
        token = data.removeprefix("reply:")
        pending = pending_replies.get(token)
        if not pending or pending.owner_id != user_id:
            await query.answer("Этот запрос уже недоступен.", show_alert=True)
            return
        clear_cold_flow(context)
        context.user_data.pop("active_conversation", None)
        context.user_data["pending_reply"] = token
        await query.answer()
        await query.message.reply_text(f"Напишите ответ для «{pending.customer_name}» по-русски. Я переведу его на {pending.language}.")
        return
    if data == "translate:incoming":
        clear_reply_flow(context)
        context.user_data["manual_translate"] = True
        await query.answer()
        await query.message.reply_text("Отправьте текст — я переведу его на русский.", reply_markup=MAIN_KEYBOARD)
        return
    if data == "translate:outgoing":
        clear_reply_flow(context)
        await query.answer()
        await show_cold_picker(query.message)
        return
    if data.startswith("template:"):
        await query.answer()
        await send_pending_reply(query.message, context, TEMPLATES[data.removeprefix("template:")])
        return
    if data.startswith("replangset:"):
        _, token, language_key = data.split(":", 2)
        pending = pending_replies.get(token)
        if not pending or pending.owner_id != user_id or language_key not in LANGUAGES:
            await query.answer("Этот запрос уже недоступен.", show_alert=True)
            return
        pending_replies[token] = PendingReply(
            pending.connection_id, pending.customer_chat_id, LANGUAGES[language_key],
            pending.customer_name, pending.owner_id,
        )
        await query.answer("Язык изменён")
        await query.message.reply_text(
            f"Язык ответа: {LANGUAGES[language_key]}. Теперь нажмите «Ответить по-русски» "
            "или используйте быстрый ответ."
        )
        return
    if data.startswith("replang:"):
        token = data.removeprefix("replang:")
        pending = pending_replies.get(token)
        if not pending or pending.owner_id != user_id:
            await query.answer("Этот запрос уже недоступен.", show_alert=True)
            return
        await query.answer()
        language_items = list(LANGUAGES.items())
        buttons = [
            [InlineKeyboardButton(label, callback_data=f"replangset:{token}:{key}") for key, label in language_items[i:i + 2]]
            for i in range(0, len(language_items), 2)
        ]
        await query.message.reply_text("Выберите правильный язык для ответа:", reply_markup=InlineKeyboardMarkup(buttons))
        return
    if data.startswith("quick:"):
        _, token, template_key = data.split(":", 2)
        pending = pending_replies.get(token)
        russian_text = TEMPLATES.get(template_key)
        if not pending or pending.owner_id != user_id or not russian_text:
            await query.answer("Этот быстрый ответ уже недоступен.", show_alert=True)
            return
        await query.answer()
        try:
            translated = await translate_text(russian_text, pending.language, settings(user_id)["tone"])
            await send_business_text(context, pending, translated)
            increment(user_id, "outgoing_count")
            context.user_data["active_conversation"] = pending
            await query.message.reply_text(
                f"✅ Быстрый ответ отправлен ({pending.language}).\n\n"
                f"💬 Беседа с «{pending.customer_name}» закреплена. Следующие сообщения будут уходить только ему."
            )
        except Exception:
            logger.exception("Could not send quick reply")
            await query.message.reply_text("Не удалось отправить быстрый ответ. Попробуйте ещё раз.")
        return
    if data.startswith("conv:"):
        token = data.removeprefix("conv:")
        active = conversation_choices.get(token)
        if not active or active.owner_id != user_id:
            await query.answer("Эта беседа уже недоступна.", show_alert=True)
            return
        await query.answer()
        items = list(LANGUAGES.items())
        buttons = [
            [InlineKeyboardButton(label, callback_data=f"convlang:{token}:{key}") for key, label in items[i:i + 2]]
            for i in range(0, len(items), 2)
        ]
        buttons.append([InlineKeyboardButton("💬 Открыть чат с клиентом", url=f"tg://user?id={active.customer_chat_id}")])
        await query.message.reply_text(
            f"Вы выбрали «{active.customer_name}». На каком языке ему писать?\n"
            f"Автоматически определено: {active.language}.",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return
    if data.startswith("convlang:"):
        _, token, language_key = data.split(":", 2)
        active = conversation_choices.get(token)
        if not active or active.owner_id != user_id or language_key not in LANGUAGES:
            await query.answer("Этот выбор уже недоступен.", show_alert=True)
            return
        new_language = LANGUAGES[language_key]
        conversation_choices[token] = PendingReply(
            active.connection_id, active.customer_chat_id, new_language, active.customer_name, active.owner_id
        )
        set_client_language(active.owner_id, active.connection_id, active.customer_chat_id, new_language)
        context.user_data.pop("waiting_cold_target", None)
        context.user_data.pop("cold_target_url", None)
        context.user_data.pop("cold_draft_language", None)
        context.user_data["active_conversation"] = active
        await query.answer("Язык выбран")
        await query.message.reply_text(
            f"💬 Беседа с «{active.customer_name}» открыта. Пишите сообщения по-русски — "
            f"я переведу их на {new_language} и отправлю в его чат.\n\n"
            "Для завершения нажмите «❌ Отмена».",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("💬 Открыть чат с клиентом", url=f"tg://user?id={active.customer_chat_id}")]]
            ),
        )
        return
    if data == "coldtarget":
        context.user_data["waiting_cold_target"] = True
        context.user_data.pop("cold_target_url", None)
        await query.answer()
        await query.message.reply_text(
            "Отправьте @username человека или ссылку вида https://t.me/username.\n\n"
            "По имени бот искать не может: Telegram не даёт ботам доступ к вашему списку чатов и "
            "поиску чужих аккаунтов."
        )
        return
    if data == "coldplain":
        clear_reply_flow(context)
        await query.answer()
        await show_cold_picker(query.message)
        return
    if data.startswith("coldtextlang:"):
        language_key = data.removeprefix("coldtextlang:")
        if language_key not in LANGUAGES:
            await query.answer("Выберите язык ещё раз.", show_alert=True)
            return
        # A cold message must never inherit an earlier live conversation.
        context.user_data.pop("pending_reply", None)
        context.user_data.pop("active_conversation", None)
        context.user_data.pop("manual_translate", None)
        context.user_data.pop("manual_voice_translate", None)
        context.user_data["cold_draft_language"] = LANGUAGES[language_key]
        await query.answer()
        await query.message.reply_text(
            f"Напишите сообщение по-русски. Я переведу его на {LANGUAGES[language_key]}."
        )
        return
    if data.startswith("adminrm:"):
        try:
            admin_id = int(data.removeprefix("adminrm:"))
        except ValueError:
            await query.answer("Не удалось распознать администратора.", show_alert=True)
            return
        if is_business_owner(admin_id):
            await query.answer("Нельзя удалить владельца подключённого Business-аккаунта.", show_alert=True)
            return
        remove_admin(admin_id)
        await query.answer("Доступ администратора удалён")
        await show_admins(query.message, edit=True)
        return
    if not data.startswith("panel:"):
        return
    action = data.removeprefix("panel:")
    await query.answer()
    if action == "home":
        await show_panel(query.message, user_id, edit=True)
    elif action == "language":
        keys = [[InlineKeyboardButton(name, callback_data=f"lang:{key}")] for key, name in LANGUAGES.items()]
        keys.append([InlineKeyboardButton("⬅️ Назад", callback_data="panel:home")])
        await query.message.edit_text("На какой язык переводить входящие сообщения?", reply_markup=InlineKeyboardMarkup(keys))
    elif action == "tone":
        keys = [[InlineKeyboardButton(name, callback_data=f"tone:{key}")] for key, name in TONES.items()]
        keys.append([InlineKeyboardButton("⬅️ Назад", callback_data="panel:home")])
        await query.message.edit_text("Выберите стиль переводимых ответов:", reply_markup=InlineKeyboardMarkup(keys))
    elif action == "templates":
        keys = [[InlineKeyboardButton(text, callback_data=f"template:{key}")] for key, text in TEMPLATES.items()]
        keys.append([InlineKeyboardButton("⬅️ Назад", callback_data="panel:home")])
        await query.message.edit_text("Быстрые ответы: сначала выберите сообщение клиента, затем шаблон.", reply_markup=InlineKeyboardMarkup(keys))
    elif action == "conversations":
        clients = recent_clients(user_id)
        if not clients:
            await query.message.edit_text(
                "Пока нет доступных людей. Человек должен сначала написать вам в личный чат, "
                "чтобы Telegram дал боту доступ к этой беседе.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="panel:home")]]),
            )
            return
        buttons = []
        for client_row in clients:
            token = secrets.token_urlsafe(8)
            conversation_choices[token] = PendingReply(
                client_row["connection_id"], client_row["chat_id"], client_row["language"], client_row["name"], user_id
            )
            buttons.append([InlineKeyboardButton(f"💬 {client_row['name']} — {client_row['language']}", callback_data=f"conv:{token}")])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="panel:home")])
        await query.message.edit_text("Выберите человека для беседы:", reply_markup=InlineKeyboardMarkup(buttons))
    elif action in {"cold", "translate"}:
        clear_reply_flow(context)
        await show_translate_start(query.message, edit=True)
    elif action == "addadmin":
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton(
                "👤 Выбрать администратора",
                request_users=KeyboardButtonRequestUsers(
                    request_id=SELECT_ADMIN_REQUEST, user_is_bot=False, max_quantity=1,
                    request_name=True, request_username=True,
                ),
            )], ["❌ Отмена"]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await query.message.reply_text(
            "Нажмите «👤 Выбрать администратора» и выберите Telegram-аккаунт, которому хотите дать доступ к боту.",
            reply_markup=keyboard,
        )
    elif action == "admins":
        await show_admins(query.message, edit=True)
    elif action == "stats":
        row = settings(user_id)
        await query.message.edit_text(
            f"📊 Статистика\n\nВходящих переведено: {row['incoming_count']}\nОтправлено ответов: {row['outgoing_count']}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="panel:home")]]),
        )
    elif action == "toggle":
        row = settings(user_id)
        set_setting(user_id, "enabled", 0 if row["enabled"] else 1)
        await show_panel(query.message, user_id, edit=True)
    elif data.startswith("lang:"):
        pass


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.answer("Доступ закрыт.", show_alert=True)
        return
    data = query.data or ""
    if data.startswith("lang:"):
        value = data.removeprefix("lang:")
        if value in LANGUAGES:
            set_setting(user_id, "incoming_language", value)
            await query.answer("Язык сохранён")
            await show_panel(query.message, user_id, edit=True)
    elif data.startswith("tone:"):
        value = data.removeprefix("tone:")
        if value in TONES:
            set_setting(user_id, "tone", value)
            await query.answer("Стиль сохранён")
            await show_panel(query.message, user_id, edit=True)


async def add_selected_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    shared = message.users_shared
    if not shared or shared.request_id != SELECT_ADMIN_REQUEST:
        return
    if not is_admin(update.effective_user.id):
        return
    selected = shared.users[0]
    name = selected.first_name or selected.username or "Выбранный аккаунт"
    add_admin(selected.user_id, name)
    await message.reply_text(
        f"✅ «{name}» добавлен в администраторы. Теперь он может открыть @perevodmel_bot и нажать /start.",
        reply_markup=MAIN_KEYBOARD,
    )


async def transcribe_voice_message(message, context: ContextTypes.DEFAULT_TYPE) -> str:
    voice = message.voice
    if not voice:
        raise RuntimeError("Voice message is missing")
    if voice.duration > 300:
        raise ValueError("Голосовое слишком длинное. Отправьте запись до 5 минут.")
    telegram_file = await context.bot.get_file(voice.file_id)
    audio = io.BytesIO(bytes(await telegram_file.download_as_bytearray()))
    audio.name = "voice.ogg"
    response = await client.audio.transcriptions.create(
        model=TRANSCRIBE_MODEL,
        file=audio,
        prompt=(
            "Transcribe accurately. The speech may be Russian, Turkmen, Tajik, Kyrgyz, Uzbek, English, "
            "Spanish, or German. Preserve informal spoken wording and names."
        ),
    )
    text = getattr(response, "text", str(response)).strip()
    if not text:
        raise RuntimeError("Empty transcription")
    return text


async def private_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.voice or not await require_admin(update):
        return
    try:
        await message.chat.send_action(ChatAction.TYPING)
        transcript = await transcribe_voice_message(message, context)
        if context.user_data.pop("manual_voice_translate", None):
            source, translated = await translate_incoming(transcript, "Русский")
            await message.reply_text(f"🎙 Распознано ({source}):\n{transcript}\n\n🇷🇺 Перевод:\n{translated}")
            return
        if context.user_data.get("pending_reply"):
            await message.reply_text(f"🎙 Распознано:\n{transcript}")
            await send_pending_reply(message, context, transcript)
            return
        if context.user_data.get("active_conversation"):
            await message.reply_text(f"🎙 Распознано:\n{transcript}")
            await send_active_message(message, context, transcript)
            return
        source, translated = await translate_incoming(transcript, "Русский")
        await message.reply_text(f"🎙 Распознано ({source}):\n{transcript}\n\n🇷🇺 Перевод:\n{translated}")
    except ValueError as error:
        await message.reply_text(str(error))
    except Exception:
        logger.exception("Voice translation failed")
        await message.reply_text("Не удалось распознать голосовое. Попробуйте отправить запись ещё раз.")


async def private_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.text:
        return
    if not await require_admin(update):
        return
    if message.text == "🌐 Перевести текст":
        clear_reply_flow(context)
        await show_translate_start(message)
        return
    if message.text == "⚙️ Панель управления":
        await show_panel(message, update.effective_user.id)
        return
    if message.text == "🌐 Перевести текст":
        context.user_data.pop("pending_reply", None)
        context.user_data.pop("active_conversation", None)
        context.user_data.pop("cold_draft_language", None)
        context.user_data["manual_translate"] = True
        await message.reply_text("Отправьте текст — я переведу его на русский.", reply_markup=MAIN_KEYBOARD)
        return
    if message.text == "🎙 Перевести голос":
        context.user_data.pop("pending_reply", None)
        context.user_data.pop("active_conversation", None)
        context.user_data.pop("cold_draft_language", None)
        context.user_data["manual_voice_translate"] = True
        await message.reply_text(
            "Отправьте сюда голосовое сообщение — я распознаю речь и переведу её на русский.",
            reply_markup=MAIN_KEYBOARD,
        )
        return
    if message.text == "📝 Холодное сообщение":
        clear_reply_flow(context)
        await show_cold_picker(message)
        return
    if message.text == "ℹ️ Как пользоваться":
        await message.reply_text(
            "1. Подключите бота в Telegram Business.\n"
            "2. Сообщение клиента придёт сюда с переводом.\n"
            "3. Нажмите «Ответить по-русски» и напишите свой ответ.\n"
            "4. Бот переведёт и отправит его клиенту.",
            reply_markup=MAIN_KEYBOARD,
        )
        return
    if message.text == "❌ Отмена":
        context.user_data.pop("pending_reply", None)
        context.user_data.pop("active_conversation", None)
        context.user_data.pop("cold_draft_language", None)
        context.user_data.pop("cold_target_url", None)
        context.user_data.pop("waiting_cold_target", None)
        context.user_data.pop("manual_translate", None)
        context.user_data.pop("manual_voice_translate", None)
        await message.reply_text("Подготовка ответа отменена.", reply_markup=MAIN_KEYBOARD)
        return
    if (
        context.user_data.get("waiting_cold_target")
        and not context.user_data.get("pending_reply")
        and not context.user_data.get("active_conversation")
    ):
        context.user_data.pop("waiting_cold_target", None)
        target_url = parse_telegram_target(message.text)
        if not target_url:
            await message.reply_text(
                "Не получилось распознать аккаунт. Отправьте, например, @username или "
                "https://t.me/username."
            )
            context.user_data["waiting_cold_target"] = True
            return
        context.user_data["cold_target_url"] = target_url
        await message.reply_text("✅ Чат выбран. Теперь выберите язык сообщения.", reply_markup=cold_language_markup())
        return
    if context.user_data.pop("manual_translate", None):
        try:
            await message.chat.send_action(ChatAction.TYPING)
            await message.reply_text(await translate_text(message.text, "Русский"))
        except Exception:
            logger.exception("Manual translation failed")
            await message.reply_text("Не удалось выполнить перевод. Попробуйте ещё раз.")
        return
    if draft_language := context.user_data.get("cold_draft_language"):
        try:
            await message.chat.send_action(ChatAction.TYPING)
            translated = await translate_text(message.text, draft_language, settings(update.effective_user.id)["tone"])
            target_url = context.user_data.get("cold_target_url")
            keyboard = (
                InlineKeyboardMarkup([[InlineKeyboardButton("💬 Открыть чат и отправить", url=target_url)]])
                if target_url else None
            )
            await message.reply_text(
                translated,
                reply_markup=keyboard,
            )
        except Exception:
            logger.exception("Cold-message translation failed")
            await message.reply_text("Не удалось подготовить перевод. Попробуйте ещё раз.")
        return
    if context.user_data.get("pending_reply"):
        await send_pending_reply(message, context, message.text)
        return
    if context.user_data.get("active_conversation"):
        await send_active_message(message, context, message.text)
        return
    try:
        await message.chat.send_action(ChatAction.TYPING)
        await message.reply_text(await translate_text(message.text, "Русский"))
    except Exception:
        logger.exception("Translation failed")
        await message.reply_text("Не удалось выполнить перевод. Проверьте настройки API.")


async def setup_commands(app: Application) -> None:
    await app.bot.set_my_commands(
        [
            BotCommand("start", "Открыть бота и кнопки"),
            BotCommand("panel", "Панель управления"),
            BotCommand("cancel", "Отменить подготовку ответа"),
            BotCommand("cold", "Подготовить холодное сообщение"),
        ]
    )


def main() -> None:
    if not TOKEN or not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Fill TELEGRAM_BOT_TOKEN and OPENAI_API_KEY in .env.")
    init_db()
    app = Application.builder().token(TOKEN).post_init(setup_commands).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", panel))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("cold", cold))
    app.add_handler(BusinessConnectionHandler(remember_business_connection))
    app.add_handler(MessageHandler(filters.UpdateType.BUSINESS_MESSAGES & filters.TEXT, receive_business_message))
    app.add_handler(CallbackQueryHandler(settings_callback, pattern=r"^(lang|tone):"))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.StatusUpdate.USERS_SHARED, add_selected_admin))
    app.add_handler(MessageHandler(filters.VOICE & ~filters.UpdateType.BUSINESS_MESSAGES, private_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, private_text))
    logger.info("Bot started with model %s", MODEL)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
