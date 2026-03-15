import aiosqlite
from collections import defaultdict
from datetime import datetime, timezone

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from bot.config import DB_PATH, LANGUAGES
from bot.logging_config import get_logger
from bot.translate import translate_to

log = get_logger()

router = Router()

MAIN_MENU_TEXTS = {
    "sk": "Hlavné menu",
    "uz": "Asosiy menyu",
    "tl": "Pangunahing menu",
    "uk": "Головне меню",
    "other": "Main menu",
}

POST_AD_TEXTS = {
    "sk": "Pridať inzerát",
    "uz": "E'lon joylash",
    "tl": "Mag-post ng ad",
    "uk": "Опублікувати оголошення",
    "other": "Post ad",
}

VIEW_ADS_TEXTS = {
    "sk": "Prezerať inzeráty",
    "uz": "E'lonlarni ko'rish",
    "tl": "Tingnan ang mga ad",
    "uk": "Переглянути оголошення",
    "other": "View ads",
}

MY_CHATS_TEXTS = {
    "sk": "Moje chaty",
    "uz": "Mening chatlarim",
    "tl": "Aking mga chat",
    "uk": "Мої чати",
    "other": "My chats",
}

NO_CHATS_TEXTS = {
    "sk": "Zatiaľ žiadne aktívne chaty.",
    "uz": "Hozircha faol chatlar yo'q.",
    "tl": "Walang aktibong mga chat pa.",
    "uk": "Поки немає активних чатів.",
    "other": "No active chats yet.",
}

BACK_TO_CHATS_TEXTS = {
    "sk": "🔙 Späť na chaty",
    "uz": "🔙 Chatlarga qaytish",
    "tl": "🔙 Bumalik sa mga chat",
    "uk": "🔙 Назад до чатів",
    "other": "🔙 Back to chats",
}

ENTER_AD_TEXT = {
    "sk": "Zadajte text inzerátu:",
    "uz": "E'lon matnini kiriting:",
    "tl": "Ilagay ang teksto ng ad:",
    "uk": "Введіть текст оголошення:",
    "other": "Enter ad text:",
}

AD_POSTED = {
    "sk": "Inzerát bol uverejnený!",
    "uz": "E'lon joylandi!",
    "tl": "Na-post na ang ad!",
    "uk": "Оголошення опубліковано!",
    "other": "Ad posted!",
}

NO_ADS = {
    "sk": "Zatiaľ žiadne inzeráty.",
    "uz": "Hozircha e'lonlar yo'q.",
    "tl": "Walang mga ad pa.",
    "uk": "Поки немає оголошень.",
    "other": "No ads yet.",
}

BACK_TEXTS = {
    "sk": "← Späť",
    "uz": "← Orqaga",
    "tl": "← Bumalik",
    "uk": "← Назад",
    "other": "← Back",
}

CANCEL_TEXTS = {
    "sk": "Zrušiť",
    "uz": "Bekor qilish",
    "tl": "Kanselahin",
    "uk": "Скасувати",
    "other": "Cancel",
}

WRITE_TO_AUTHOR_TEXTS = {
    "sk": "✉️ Napísať autorovi",
    "uz": "✉️ Muallifga yozish",
    "tl": "✉️ Sumulat sa may-akda",
    "uk": "✉️ Написати автору",
    "other": "✉️ Write to author",
}

BACK_EMOJI_TEXTS = {"sk": "🔙 Späť", "uz": "🔙 Orqaga", "tl": "🔙 Bumalik", "uk": "🔙 Назад", "other": "🔙 Back"}

RELAY_INTERESTED_TEXTS = {
    "sk": "Niekto má záujem o váš inzerát:",
    "uz": "Kimdir sizning e'loningizga qiziqyapti:",
    "tl": "May interesado sa iyong ad:",
    "uk": "Хтось зацікавлений у вашому оголошенні:",
    "other": "Someone is interested in your ad:",
}

def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    try:
        return {k: row[k] for k in row.keys()}
    except Exception:
        return dict(row) if row else None
RELAY_REPLY_BTN_TEXTS = {"sk": "✉️ Odpovedať", "uz": "✉️ Javob berish", "tl": "✉️ Sumagot", "uk": "✉️ Відповісти", "other": "✉️ Reply"}
RELAY_CHAT_HEADER_TEXTS = {
    "sk": "Chat k inzerátu. Napíšte správu:",
    "uz": "E'lon bo'yicha chat. Xabar yozing:",
    "tl": "Chat tungkol sa ad. Mag-type ng mensahe:",
    "uk": "Чат щодо оголошення. Напишіть повідомлення:",
    "other": "Chat about your ad. Type your message:",
}
RELAY_STOP_TEXTS = {"sk": "🔙 Ukončiť chat", "uz": "🔙 Chatni tugatish", "tl": "🔙 I-stop ang chat", "uk": "🔙 Зупинити чат", "other": "🔙 End chat"}

RELAY_HEADER_CHAT_WITH = {"sk": "💬 Chat s", "uz": "💬 Chat", "tl": "💬 Chat sa", "uk": "💬 Чат з", "other": "💬 Chat with"}
RELAY_HEADER_ABOUT = {"sk": "O inzeráte:", "uz": "E'lon:", "tl": "Tungkol sa:", "uk": "Про оголошення:", "other": "About:"}
RELAY_HEADER_TYPE_BELOW = {"sk": "Napíšte správu nižšie:", "uz": "Xabar yozing:", "tl": "Mag-type ng mensahe sa ibaba:", "uk": "Напишіть повідомлення нижче:", "other": "Type your message below:"}

CONNECTING_TEXTS = {
    "sk": "Pripájam vás s autorom...",
    "uz": "Sizni muallif bilan bog'layapmiz...",
    "tl": "Ikino-connect ka sa may-akda...",
    "uk": "З'єдную з автором...",
    "other": "Connecting you with the author...",
}

NEW_MESSAGE_FROM_TEXTS = {
    "sk": "💬 Nová správa od",
    "uz": "💬 Yangi xabar",
    "tl": "💬 Bagong mensahe mula sa",
    "uk": "💬 Нове повідомлення від",
    "other": "💬 New message from",
}
OPEN_CHAT_BTN_TEXTS = {
    "sk": "Otvorit chat",
    "uz": "Chatni ochish",
    "tl": "Buksan ang chat",
    "uk": "Відкрити чат",
    "other": "Open chat",
}

CHOOSE_LANG_TEXT = "Choose language / Vyberte jazyk / Tilni tanlang / Pumili ng wika / Оберіть мову:"

LANG_BUTTON_TEXTS = {
    "sk": "🇸🇰 Slovak",
    "uz": "🇺🇿 Uzbek",
    "tl": "🇵🇭 Tagalog",
    "uk": "🇺🇦 Ukrainian",
    "other": "🌐 Other",
}


def _days_left(expires_at: str | None) -> str:
    if not expires_at:
        return "? days left"
    try:
        # SQLite returns "YYYY-MM-DD HH:MM:SS" (UTC or local)
        end = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = (end - now).days
        if delta < 0:
            return "0 days left"
        if delta == 1:
            return "1 day left"
        return f"{delta} days left"
    except (ValueError, TypeError):
        return "? days left"


def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=LANG_BUTTON_TEXTS.get(code, name), callback_data=f"lang_{code}")]
            for code, name in LANGUAGES.items()
        ]
    )


def main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=POST_AD_TEXTS[lang], callback_data="post_ad")],
            [InlineKeyboardButton(text=VIEW_ADS_TEXTS[lang], callback_data="view_ads")],
            [InlineKeyboardButton(text=MY_CHATS_TEXTS.get(lang, MY_CHATS_TEXTS["other"]), callback_data="my_chats")],
        ]
    )


def back_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BACK_TEXTS[lang], callback_data="back_to_menu")]
        ]
    )


def cancel_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=CANCEL_TEXTS[lang], callback_data="back_to_menu")]
        ]
    )


async def save_user_message(user_id: int, chat_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO users (user_id, language, chat_id, message_id) VALUES (?, 'other', ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET chat_id = excluded.chat_id, message_id = excluded.message_id""",
            (user_id, chat_id, message_id),
        )
        await db.commit()


async def get_user_message_ids(user_id: int) -> tuple[int | None, int | None]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT chat_id, message_id FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if row and row["chat_id"] is not None and row["message_id"] is not None:
                return int(row["chat_id"]), int(row["message_id"])
            return None, None


async def edit_user_message(
    bot: Bot, user_id: int, text: str, reply_markup: InlineKeyboardMarkup | None = None
) -> bool:
    chat_id, message_id = await get_user_message_ids(user_id)
    if chat_id is None or message_id is None:
        return False
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
        )
        return True
    except Exception:
        return False


async def get_user_language(user_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT language FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row["language"] if row else "other"


USER_STATE_MAIN_MENU = "MAIN_MENU"
USER_STATE_VIEWING_ADS = "VIEWING_ADS"
USER_STATE_POSTING_AD = "POSTING_AD"
USER_STATE_MY_CHATS = "MY_CHATS"
USER_STATE_IN_RELAY = "IN_RELAY"


async def get_user_state(user_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT state FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if row and row["state"]:
                return str(row["state"])
            return USER_STATE_MAIN_MENU


async def set_user_state_db(user_id: int, state: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO users (user_id, state) VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET state = excluded.state""",
            (user_id, state),
        )
        await db.commit()


async def get_user_current_relay_id(user_id: int) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT current_relay_id FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if row and row[0] is not None:
                return int(row[0])
            return None


async def set_user_current_relay_id(user_id: int, session_id: int | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET current_relay_id = ? WHERE user_id = ?", (session_id, user_id))
        await db.commit()


async def set_user_language(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (user_id, language) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET language = excluded.language",
            (user_id, lang),
        )
        await db.commit()


async def save_ad(user_id: int, language: str, text: str, author_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ads (user_id, language, content, author_name) VALUES (?, ?, ?, ?)",
            (user_id, language, text, author_name),
        )
        await db.commit()


async def get_ads_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM ads WHERE expires_at > datetime('now')"
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def get_last_ads(limit: int = 10, offset: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT id, user_id, language, content, author_name, created_at, expires_at
               FROM ads WHERE expires_at > datetime('now') ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (limit, offset),
        ) as cur:
            return [_row_to_dict(row) or dict(row) for row in await cur.fetchall()]


async def get_ad_by_id(ad_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, user_id, language, content, author_name FROM ads WHERE id = ?",
            (ad_id,),
        ) as cur:
            row = await cur.fetchone()
            return _row_to_dict(row)


async def get_user_chat_id(user_id: int) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT chat_id FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row and row[0] is not None else None


async def view_ads_clear_messages(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM view_ads_messages WHERE user_id = ?", (user_id,))
        await db.commit()


async def view_ads_add_message(user_id: int, chat_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO view_ads_messages (user_id, chat_id, message_id) VALUES (?, ?, ?)",
            (user_id, chat_id, message_id),
        )
        await db.commit()


async def view_ads_get_messages(user_id: int) -> list[tuple[int, int]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT chat_id, message_id FROM view_ads_messages WHERE user_id = ?",
            (user_id,),
        ) as cur:
            return [(int(row[0]), int(row[1])) for row in await cur.fetchall()]


def write_to_author_keyboard(lang: str, ad_id: int) -> InlineKeyboardMarkup:
    write_t = WRITE_TO_AUTHOR_TEXTS.get(lang, WRITE_TO_AUTHOR_TEXTS["other"])
    data = f"{CALLBACK_REPLY_AD_PREFIX}{int(ad_id)}"[:64]  # Telegram limit 64 bytes
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=write_t, callback_data=data)]]
    )


def view_ads_back_keyboard(lang: str) -> InlineKeyboardMarkup:
    back_t = BACK_EMOJI_TEXTS.get(lang, BACK_EMOJI_TEXTS["other"])
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=back_t, callback_data="back_to_menu")]]
    )


def view_ads_last_ad_keyboard(lang: str, ad_id: int) -> InlineKeyboardMarkup:
    """Keyboard for the last ad: Write to author + Back button."""
    write_t = WRITE_TO_AUTHOR_TEXTS.get(lang, WRITE_TO_AUTHOR_TEXTS["other"])
    back_t = BACK_EMOJI_TEXTS.get(lang, BACK_EMOJI_TEXTS["other"])
    data = f"{CALLBACK_REPLY_AD_PREFIX}{int(ad_id)}"[:64]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=write_t, callback_data=data)],
            [InlineKeyboardButton(text=back_t, callback_data="back_to_menu")],
        ]
    )


async def _build_single_ad_text(ad: dict, viewer_lang: str, ad_id: int = 0) -> str:
    """Build ad display text. Always translate to VIEWER's language (source language detected by OpenAI)."""
    name = ad["author_name"] or "Unknown"
    days_left = _days_left(ad.get("expires_at"))
    content = ad["content"]
    viewer_lang = (viewer_lang or "other").strip() or "other"
    target_language_name = LANGUAGES.get(viewer_lang, "Other")
    print(f"DEBUG: translating ad {ad_id} to {viewer_lang} ({target_language_name})")
    content = await translate_to(content, target_language_name)
    return f"👤 {name}\n· {days_left}\n\n{content}"


VIEW_ADS_MAX = 30

# Must match exactly: button callback_data and handler filter (max 64 bytes for Telegram)
CALLBACK_REPLY_AD_PREFIX = "reply_ad_"


async def relay_create(user_a: int, user_b: int, ad_id: int, viewer_name: str = "") -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO relay_sessions (user_a, user_b, ad_id, viewer_name, status) VALUES (?, ?, ?, ?, 'active')",
            (user_a, user_b, ad_id, viewer_name or ""),
        )
        await db.commit()
        return cur.lastrowid


async def relay_get_active_sessions_for_user(user_id: int) -> list:
    """All active relay sessions where user is participant (user_a or user_b)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT id, user_a, user_b, ad_id, viewer_name, author_joined, status
               FROM relay_sessions WHERE status = 'active' AND (user_a = ? OR user_b = ?) ORDER BY id DESC""",
            (user_id, user_id),
        ) as cur:
            return [_row_to_dict(row) or dict(row) for row in await cur.fetchall()]


async def relay_get_session_by_id(session_id: int, active_only: bool = True) -> dict | None:
    """Get session by id. If active_only, only return when status='active'."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        q = """SELECT id, user_a, user_b, ad_id, viewer_name, author_joined, status
               FROM relay_sessions WHERE id = ?"""
        if active_only:
            q += " AND status = 'active'"
        async with db.execute(q, (session_id,)) as cur:
            row = await cur.fetchone()
            return _row_to_dict(row) if row else None


async def relay_set_author_joined(relay_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE relay_sessions SET author_joined = 1 WHERE id = ?", (relay_id,))
        await db.commit()


async def relay_get_other_user(session: dict, user_id: int) -> int:
    return session["user_b"] if session["user_a"] == user_id else session["user_a"]


async def relay_add_message(relay_id: int, from_user_id: int, from_name: str, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO relay_messages (relay_id, from_user_id, from_name, content) VALUES (?, ?, ?, ?)",
            (relay_id, from_user_id, from_name, content),
        )
        await db.commit()


async def relay_get_messages(relay_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT from_user_id, from_name, content FROM relay_messages WHERE relay_id = ? ORDER BY id",
            (relay_id,),
        ) as cur:
            return [_row_to_dict(row) or dict(row) for row in await cur.fetchall()]


async def relay_close(relay_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE relay_sessions SET status = 'closed' WHERE id = ?", (relay_id,))
        await db.commit()


def relay_keyboard(lang: str, session_id: int) -> InlineKeyboardMarkup:
    back_chats_t = BACK_TO_CHATS_TEXTS.get(lang, BACK_TO_CHATS_TEXTS["other"])
    stop_t = RELAY_STOP_TEXTS.get(lang, RELAY_STOP_TEXTS["other"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=back_chats_t, callback_data="back_to_chats")],
            [InlineKeyboardButton(text=stop_t, callback_data=f"relay_stop_{session_id}")],
        ]
    )


def _relay_opening_text(lang: str, other_name: str, ad_preview: str) -> str:
    chat_with = RELAY_HEADER_CHAT_WITH.get(lang, RELAY_HEADER_CHAT_WITH["other"])
    about = RELAY_HEADER_ABOUT.get(lang, RELAY_HEADER_ABOUT["other"])
    type_below = RELAY_HEADER_TYPE_BELOW.get(lang, RELAY_HEADER_TYPE_BELOW["other"])
    return f"{chat_with} {other_name}\n{about} {ad_preview}\n\n{type_below}"


async def _delete_all_bot_messages_for_user(bot: Bot, user_id: int, except_message_id: int | None = None):
    """Delete main message and all view_ads messages for this user. Optionally keep one message (e.g. the relay UI)."""
    chat_id, main_msg_id = await get_user_message_ids(user_id)
    if chat_id is None:
        return
    to_delete = []
    if main_msg_id is not None and main_msg_id != except_message_id:
        to_delete.append((chat_id, main_msg_id))
    for cid, mid in await view_ads_get_messages(user_id):
        if (cid, mid) != (chat_id, except_message_id):
            to_delete.append((cid, mid))
    for cid, mid in to_delete:
        try:
            await bot.delete_message(chat_id=cid, message_id=mid)
        except Exception:
            pass
    await view_ads_clear_messages(user_id)


async def _build_relay_ui_text(relay_id: int, for_user_id: int, lang: str, header: bool = True) -> str:
    target_lang_name = LANGUAGES.get(lang, "Other")
    messages = await relay_get_messages(relay_id)
    lines = []
    for m in messages:
        name = m["from_name"] or "?"
        content = m["content"]
        if m["from_user_id"] != for_user_id:
            content = await translate_to(content, target_lang_name)
        lines.append(f"{name}: {content}")
    thread = "\n".join(lines)
    if not header:
        return thread
    header_text = RELAY_CHAT_HEADER_TEXTS.get(lang, RELAY_CHAT_HEADER_TEXTS["other"])
    return header_text + "\n\n" + thread if thread else header_text + "\n\n"


async def _draw_main_menu(bot: Bot, user_id: int, chat_id: int, *, text: str | None = None, reply_markup=None):
    lang = await get_user_language(user_id)
    if text is None:
        text = MAIN_MENU_TEXTS.get(lang, MAIN_MENU_TEXTS["other"])
    if reply_markup is None:
        reply_markup = main_menu_keyboard(lang)
    sent = await bot.send_message(chat_id, text, reply_markup=reply_markup)
    await save_user_message(user_id, chat_id, sent.message_id)


async def _draw_viewing_ads(bot: Bot, user_id: int, chat_id: int):
    viewer_lang = await get_user_language(user_id)
    ads = await get_last_ads(limit=VIEW_ADS_MAX, offset=0)
    if not ads:
        msg = NO_ADS.get(viewer_lang, NO_ADS["other"])
        sent = await bot.send_message(chat_id, msg, reply_markup=view_ads_back_keyboard(viewer_lang))
        await save_user_message(user_id, chat_id, sent.message_id)
        return
    for i, ad in enumerate(ads):
        ad_id = int(ad.get("id", 0)) if isinstance(ad, dict) else getattr(ad, "id", 0)
        text = await _build_single_ad_text(ad, viewer_lang, ad_id)
        if len(text) > 4000:
            text = text[:3997] + "..."
        is_last = i == len(ads) - 1
        kb = view_ads_last_ad_keyboard(viewer_lang, ad_id) if is_last else write_to_author_keyboard(viewer_lang, ad_id)
        sent = await bot.send_message(chat_id, text, reply_markup=kb)
        await view_ads_add_message(user_id, chat_id, sent.message_id)
        if is_last:
            await save_user_message(user_id, chat_id, sent.message_id)


async def _draw_posting_ad(bot: Bot, user_id: int, chat_id: int):
    lang = await get_user_language(user_id)
    prompt = ENTER_AD_TEXT.get(lang, ENTER_AD_TEXT["other"])
    sent = await bot.send_message(chat_id, prompt, reply_markup=cancel_keyboard(lang))
    await save_user_message(user_id, chat_id, sent.message_id)


def _ad_preview_short(content: str, max_len: int = 200) -> str:
    if not content:
        return ""
    return (content.strip()[:max_len] + "...") if len(content) > max_len else content.strip()


async def _draw_my_chats(bot: Bot, user_id: int, chat_id: int):
    lang = await get_user_language(user_id)
    sessions = await relay_get_active_sessions_for_user(user_id)
    if not sessions:
        msg = NO_CHATS_TEXTS.get(lang, NO_CHATS_TEXTS["other"])
        back_t = BACK_EMOJI_TEXTS.get(lang, BACK_EMOJI_TEXTS["other"])
        sent = await bot.send_message(
            chat_id, msg,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=back_t, callback_data="back_to_menu")]]),
        )
        await save_user_message(user_id, chat_id, sent.message_id)
        return
    by_ad: dict[int, list] = defaultdict(list)
    for s in sessions:
        by_ad[int(s["ad_id"])].append(s)
    lines = []
    keyboard_buttons = []
    target_lang_name = LANGUAGES.get(lang, "Other")
    for ad_id, ad_sessions in sorted(by_ad.items(), key=lambda x: -x[0]):
        ad = await get_ad_by_id(ad_id)
        if not ad:
            continue
        content = ad.get("content") or ""
        preview = await translate_to(_ad_preview_short(content, 180), target_lang_name)
        lines.append(f"📌 {preview}")
        for s in ad_sessions:
            other_id = s["user_b"] if int(s["user_a"]) == user_id else s["user_a"]
            if int(s["user_a"]) == user_id:
                partner_name = (ad.get("author_name") or "Author")[:30]
            else:
                partner_name = (s.get("viewer_name") or "Someone")[:30]
            lines.append(f"  💬 {partner_name}")
            chat_btn = f"💬 {partner_name}"
            keyboard_buttons.append([InlineKeyboardButton(text=chat_btn, callback_data=f"open_relay_{s['id']}")])
    back_t = BACK_EMOJI_TEXTS.get(lang, BACK_EMOJI_TEXTS["other"])
    keyboard_buttons.append([InlineKeyboardButton(text=back_t, callback_data="back_to_menu")])
    title = MY_CHATS_TEXTS.get(lang, MY_CHATS_TEXTS["other"])
    text = f"{title}\n\n" + "\n".join(lines) if lines else NO_CHATS_TEXTS.get(lang, NO_CHATS_TEXTS["other"])
    if len(text) > 4000:
        text = text[:3997] + "..."
    sent = await bot.send_message(
        chat_id, text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
    )
    await save_user_message(user_id, chat_id, sent.message_id)


async def _draw_in_relay(bot: Bot, user_id: int, chat_id: int):
    relay_id = await get_user_current_relay_id(user_id)
    session = await relay_get_session_by_id(relay_id) if relay_id else None
    if not session or (int(session.get("user_a", 0)) != user_id and int(session.get("user_b", 0)) != user_id):
        await set_user_current_relay_id(user_id, None)
        await set_user_state_db(user_id, USER_STATE_MAIN_MENU)
        await _draw_main_menu(bot, user_id, chat_id)
        return
    lang = await get_user_language(user_id)
    text = await _build_relay_ui_text(session["id"], user_id, lang)
    if len(text) > 4000:
        text = text[:3997] + "..."
    sent = await bot.send_message(chat_id, text, reply_markup=relay_keyboard(lang, session["id"]))
    await save_user_message(user_id, chat_id, sent.message_id)


async def set_state(
    bot: Bot,
    user_id: int,
    new_state: str,
    chat_id: int | None = None,
    override_text: str | None = None,
    override_kb: InlineKeyboardMarkup | None = None,
):
    """Single state transition: delete all previous bot messages, update state, draw fresh screen."""
    cid = chat_id or (await get_user_message_ids(user_id))[0] or await get_user_chat_id(user_id)
    if cid is None:
        log.warning("set_state: no chat_id for user_id=%s", user_id)
        return
    await set_user_state_db(user_id, new_state)
    await _delete_all_bot_messages_for_user(bot, user_id)
    if override_text is not None:
        sent = await bot.send_message(cid, override_text, reply_markup=override_kb)
        await save_user_message(user_id, cid, sent.message_id)
        return
    if new_state == USER_STATE_MAIN_MENU:
        await set_user_current_relay_id(user_id, None)
        await _draw_main_menu(bot, user_id, cid)
    elif new_state == USER_STATE_VIEWING_ADS:
        await _draw_viewing_ads(bot, user_id, cid)
    elif new_state == USER_STATE_POSTING_AD:
        await _draw_posting_ad(bot, user_id, cid)
    elif new_state == USER_STATE_MY_CHATS:
        await set_user_current_relay_id(user_id, None)
        await _draw_my_chats(bot, user_id, cid)
    elif new_state == USER_STATE_IN_RELAY:
        await _draw_in_relay(bot, user_id, cid)
    else:
        await _draw_main_menu(bot, user_id, cid)


@router.message(CommandStart())
async def cmd_start(message: Message):
    try:
        user_id = message.from_user.id
        log.info("User %s started bot", user_id)
        chat_id = message.chat.id
        bot = message.bot
        chat_id_stored, message_id_stored = await get_user_message_ids(user_id)
        if chat_id_stored is not None and message_id_stored is not None:
            try:
                await bot.edit_message_text(
                    chat_id=chat_id_stored,
                    message_id=message_id_stored,
                    text=CHOOSE_LANG_TEXT,
                    reply_markup=lang_keyboard(),
                )
                await save_user_message(user_id, chat_id_stored, message_id_stored)
                return
            except Exception as e:
                log.debug("Could not edit existing message: %s", e)
        sent = await message.answer(CHOOSE_LANG_TEXT, reply_markup=lang_keyboard())
        await save_user_message(user_id, chat_id, sent.message_id)
    except Exception:
        log.exception("cmd_start failed")


@router.callback_query(F.data.startswith("lang_"))
async def on_language(callback: CallbackQuery):
    try:
        await callback.answer()
        lang = callback.data.replace("lang_", "")
        if lang not in LANGUAGES:
            lang = "other"
        await set_user_language(callback.from_user.id, lang)
        log.info("User %s chose language %s", callback.from_user.id, lang)
        await set_state(callback.bot, callback.from_user.id, USER_STATE_MAIN_MENU, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_language failed")


@router.callback_query(F.data == "back_to_menu")
async def on_back_to_menu(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await callback.answer()
        await set_state(callback.bot, callback.from_user.id, USER_STATE_MAIN_MENU, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_back_to_menu failed")


@router.callback_query(F.data == "post_ad")
async def on_post_ad(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await callback.answer()
        await set_state(callback.bot, callback.from_user.id, USER_STATE_POSTING_AD, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_post_ad failed")


@router.callback_query(F.data == "view_ads")
async def on_view_ads(callback: CallbackQuery):
    try:
        await callback.answer()
        await set_state(callback.bot, callback.from_user.id, USER_STATE_VIEWING_ADS, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_view_ads failed")


@router.callback_query(F.data == "my_chats")
async def on_my_chats(callback: CallbackQuery):
    try:
        await callback.answer()
        await set_state(callback.bot, callback.from_user.id, USER_STATE_MY_CHATS, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_my_chats failed")


@router.callback_query(F.data == "back_to_chats")
async def on_back_to_chats(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await callback.answer()
        await set_user_current_relay_id(callback.from_user.id, None)
        await set_state(callback.bot, callback.from_user.id, USER_STATE_MY_CHATS, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_back_to_chats failed")


@router.callback_query(F.data.startswith(CALLBACK_REPLY_AD_PREFIX))
async def on_reply_ad(callback: CallbackQuery):
    try:
        await callback.answer()
        raw = callback.data or ""
        if not raw.startswith(CALLBACK_REPLY_AD_PREFIX):
            return
        suffix = raw[len(CALLBACK_REPLY_AD_PREFIX) :].strip()
        try:
            ad_id = int(suffix)
        except ValueError:
            log.warning("reply_ad: invalid ad_id suffix=%r", suffix)
            return
        ad = await get_ad_by_id(ad_id)
        if not ad:
            log.warning("reply_ad: ad_id=%s not found", ad_id)
            return
        viewer_id = callback.from_user.id
        author_id = int(ad["user_id"])
        viewer_name = callback.from_user.first_name or callback.from_user.username or "Someone"
        log.info("User %s tapped Write to author: viewer=%s, author=%s, ad_id=%s", viewer_id, viewer_id, author_id, ad_id)
        chat_id = callback.message.chat.id
        bot = callback.bot
        session_id = await relay_create(viewer_id, author_id, ad_id, viewer_name=viewer_name)
        log.info("Relay session started: session_id=%s, user_a=%s, user_b=%s, ad_id=%s", session_id, viewer_id, author_id, ad_id)
        await set_user_current_relay_id(viewer_id, session_id)
        lang_viewer = await get_user_language(viewer_id)
        opening_english = f"💬 Chat with {ad.get('author_name') or 'Author'}\nAbout: {(ad.get('content') or '')[:300]}{'...' if len(ad.get('content') or '') > 300 else ''}\n\nType your message below:"
        opening_text = await translate_to(opening_english, LANGUAGES.get(lang_viewer, "Other"))
        await set_state(
            bot, viewer_id, USER_STATE_IN_RELAY, chat_id=chat_id,
            override_text=opening_text, override_kb=relay_keyboard(lang_viewer, session_id),
        )
    except Exception:
        log.exception("reply_ad failed")


@router.callback_query(F.data.startswith("open_relay_"))
async def on_open_relay(callback: CallbackQuery):
    """Open a specific relay (from My chats or from notification)."""
    try:
        await callback.answer()
        try:
            session_id = int(callback.data.replace("open_relay_", "").strip())
        except ValueError:
            return
        session = await relay_get_session_by_id(session_id, active_only=True)
        if not session:
            return
        user_id = callback.from_user.id
        if int(session.get("user_a", 0)) != user_id and int(session.get("user_b", 0)) != user_id:
            return
        try:
            await callback.message.delete()
        except Exception:
            pass
        await set_user_current_relay_id(user_id, session_id)
        await set_state(callback.bot, user_id, USER_STATE_IN_RELAY, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_open_relay failed")


@router.callback_query(F.data.startswith("relay_reply_"))
async def on_relay_reply(callback: CallbackQuery):
    try:
        await callback.answer()
        try:
            session_id = int(callback.data.replace("relay_reply_", ""))
        except ValueError:
            return
        session = await relay_get_session_by_id(session_id, active_only=True)
        if not session or int(session.get("user_b", 0)) != callback.from_user.id:
            return
        author_id = callback.from_user.id
        log.info("User %s joined relay session_id=%s", author_id, session_id)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await set_user_current_relay_id(author_id, session_id)
        await set_state(callback.bot, author_id, USER_STATE_IN_RELAY, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_relay_reply failed")


@router.callback_query(F.data.startswith("relay_stop_"))
async def on_relay_stop(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await callback.answer()
        try:
            session_id = int(callback.data.replace("relay_stop_", "").strip())
        except ValueError:
            return
        session = await relay_get_session_by_id(session_id, active_only=True)
        if not session:
            return
        user_id = callback.from_user.id
        if int(session.get("user_a", 0)) != user_id and int(session.get("user_b", 0)) != user_id:
            return
        user_a_id = int(session["user_a"])
        user_b_id = int(session["user_b"])
        log.info("Relay session ended: session_id=%s, user_a=%s, user_b=%s", session_id, user_a_id, user_b_id)
        bot = callback.bot
        await relay_close(session_id)
        await set_user_current_relay_id(user_a_id, None)
        await set_user_current_relay_id(user_b_id, None)
        for uid in (user_a_id, user_b_id):
            lang = await get_user_language(uid)
            lang_name = LANGUAGES.get(lang, "Other")
            chat_ended = await translate_to("Chat ended.", lang_name)
            menu_text = MAIN_MENU_TEXTS.get(lang, MAIN_MENU_TEXTS["other"])
            override = f"{chat_ended}\n\n{menu_text}"
            await set_state(bot, uid, USER_STATE_MAIN_MENU, override_text=override, override_kb=main_menu_keyboard(lang))
    except Exception:
        log.exception("on_relay_stop failed")


def _format_user_text(raw: str) -> str:
    """Clean format for display: strip, normalize newlines, limit length."""
    if not raw:
        return ""
    text = "\n".join(line.strip() for line in (raw or "").strip().splitlines())
    return text[:4000] if len(text) > 4000 else text


@router.message(F.text)
async def on_text_message(message: Message):
    """Single handler for all text: delete user message, show ⏳, then process and show result."""
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        bot = message.bot
        try:
            await message.delete()
        except Exception:
            pass
        state = await get_user_state(user_id)

        if state == USER_STATE_POSTING_AD:
            processing = await translate_to("⏳ Publishing...", LANGUAGES.get(await get_user_language(user_id), "Other"))
            proc_msg = await bot.send_message(chat_id, processing)
            lang = await get_user_language(user_id)
            raw = (message.text or "").strip()
            author_name = message.from_user.full_name or message.from_user.username or str(user_id)
            await save_ad(user_id, lang, raw, author_name)
            formatted = _format_user_text(raw)
            confirm = await translate_to("Ad published.", LANGUAGES.get(lang, "Other"))
            result_text = f"✅ {confirm}\n\n{formatted}"
            menu_text = MAIN_MENU_TEXTS.get(lang, MAIN_MENU_TEXTS["other"])
            try:
                await proc_msg.delete()
            except Exception:
                pass
            await set_state(
                bot, user_id, USER_STATE_MAIN_MENU, chat_id=chat_id,
                override_text=result_text + "\n\n" + menu_text, override_kb=main_menu_keyboard(lang),
            )
            return
        if state == USER_STATE_IN_RELAY:
            relay_id = await get_user_current_relay_id(user_id)
            session = await relay_get_session_by_id(relay_id) if relay_id else None
            if not session:
                await set_state(bot, user_id, USER_STATE_MAIN_MENU, chat_id=chat_id)
                return
            proc_msg = await bot.send_message(chat_id, "⏳")
            from_name = message.from_user.first_name or message.from_user.username or str(user_id)
            original = message.text or ""
            await relay_add_message(session["id"], user_id, from_name, original)
            other_id = await relay_get_other_user(session, user_id)
            other_lang = await get_user_language(other_id)
            other_lang_name = LANGUAGES.get(other_lang, "Other")
            log.info("Relay message forwarded: from=%s to=%s", user_id, other_id)
            my_lang = await get_user_language(user_id)
            text_for_me = await _build_relay_ui_text(session["id"], user_id, my_lang)
            if len(text_for_me) > 4000:
                text_for_me = text_for_me[:3997] + "..."
            kb_me = relay_keyboard(my_lang, session["id"])
            try:
                await proc_msg.delete()
            except Exception:
                pass
            await edit_user_message(bot, user_id, text_for_me, kb_me)

            other_state = await get_user_state(other_id)
            author_joined = int(session.get("author_joined") or 0)
            is_author = other_id == int(session["user_b"])
            if other_state in (USER_STATE_VIEWING_ADS, USER_STATE_POSTING_AD):
                other_chat_id = await get_user_chat_id(other_id)
                if other_chat_id:
                    ad = await get_ad_by_id(int(session.get("ad_id", 0)))
                    if is_author:
                        sender_name = session.get("viewer_name") or "Someone"
                    else:
                        sender_name = (ad.get("author_name") if ad else None) or "Someone"
                    ad_preview = _ad_preview_short(ad.get("content") or "", 120) if ad else ""
                    if ad_preview:
                        ad_preview = await translate_to(ad_preview, LANGUAGES.get(await get_user_language(other_id), "Other"))
                    lang_other = await get_user_language(other_id)
                    label = NEW_MESSAGE_FROM_TEXTS.get(lang_other, NEW_MESSAGE_FROM_TEXTS["other"])
                    open_btn = OPEN_CHAT_BTN_TEXTS.get(lang_other, OPEN_CHAT_BTN_TEXTS["other"])
                    notification_text = f"{label} {sender_name}"
                    if ad_preview:
                        notification_text += f"\n\n📌 {ad_preview}"
                    await bot.send_message(
                        other_chat_id,
                        notification_text,
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=[[InlineKeyboardButton(text=open_btn, callback_data=f"open_relay_{session['id']}")]]
                        ),
                    )
            elif is_author and not author_joined:
                author_chat_id = await get_user_chat_id(other_id)
                if author_chat_id:
                    text_for_other = await _build_relay_ui_text(session["id"], other_id, other_lang, header=False)
                    if len(text_for_other) > 4000:
                        text_for_other = text_for_other[:3997] + "..."
                    await set_state(
                        bot, other_id, USER_STATE_IN_RELAY, chat_id=author_chat_id,
                        override_text=text_for_other, override_kb=relay_keyboard(other_lang, session["id"]),
                    )
                await relay_set_author_joined(session["id"])
            else:
                text_for_other = await _build_relay_ui_text(session["id"], other_id, other_lang)
                if len(text_for_other) > 4000:
                    text_for_other = text_for_other[:3997] + "..."
                await edit_user_message(bot, other_id, text_for_other, relay_keyboard(other_lang, session["id"]))
            return
        if state in (USER_STATE_MAIN_MENU, USER_STATE_VIEWING_ADS, USER_STATE_MY_CHATS):
            proc_msg = await bot.send_message(chat_id, "⏳")
            await set_state(bot, user_id, state, chat_id=chat_id)
            try:
                await proc_msg.delete()
            except Exception:
                pass
    except Exception:
        log.exception("on_text_message failed")
