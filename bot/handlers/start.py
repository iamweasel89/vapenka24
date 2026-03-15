import aiosqlite
from datetime import datetime, timezone

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.config import DB_PATH, LANGUAGES
from bot.logging_config import get_logger
from bot.translate import translate_to

log = get_logger()


class PostAdStates(StatesGroup):
    waiting_text = State()


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
RELAY_STOP_TEXTS = {"sk": "🔙 Ukončiť chat", "uz": "🔙 Chatni tugatish", "tl": "🔙 I-stop ang chat", "uk": "🔙 Зупинити чат", "other": "🔙 Stop chat"}

CONNECTING_TEXTS = {
    "sk": "Pripájam vás s autorom...",
    "uz": "Sizni muallif bilan bog'layapmiz...",
    "tl": "Ikino-connect ka sa may-akda...",
    "uk": "З'єдную з автором...",
    "other": "Connecting you with the author...",
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


async def _build_single_ad_text(ad: dict, lang: str) -> str:
    name = ad["author_name"] or "Unknown"
    days_left = _days_left(ad.get("expires_at"))
    content = ad["content"]
    if ad.get("language") != lang:
        content = await translate_to(content, LANGUAGES.get(lang, "Other"))
    return f"👤 {name}\n· {days_left}\n\n{content}"


VIEW_ADS_MAX = 30

# Must match exactly: button callback_data and handler filter (max 64 bytes for Telegram)
CALLBACK_REPLY_AD_PREFIX = "reply_ad_"


async def relay_create(user_a: int, user_b: int, ad_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO relay_sessions (user_a, user_b, ad_id) VALUES (?, ?, ?)",
            (user_a, user_b, ad_id),
        )
        await db.commit()
        return cur.lastrowid


async def relay_get_active_for_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, user_a, user_b, ad_id FROM relay_sessions WHERE user_a = ? OR user_b = ? ORDER BY id DESC LIMIT 1",
            (user_id, user_id),
        ) as cur:
            row = await cur.fetchone()
            return _row_to_dict(row)


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
        await db.execute("DELETE FROM relay_sessions WHERE id = ?", (relay_id,))
        await db.commit()


def relay_keyboard(lang: str, session_id: int) -> InlineKeyboardMarkup:
    stop_t = RELAY_STOP_TEXTS.get(lang, RELAY_STOP_TEXTS["other"])
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=stop_t, callback_data=f"relay_stop_{session_id}")]]
    )


async def _build_relay_ui_text(relay_id: int, for_user_id: int, lang: str) -> str:
    header = RELAY_CHAT_HEADER_TEXTS.get(lang, RELAY_CHAT_HEADER_TEXTS["other"])
    target_lang_name = LANGUAGES.get(lang, "Other")
    messages = await relay_get_messages(relay_id)
    if not messages:
        return header + "\n\n"
    lines = []
    for m in messages:
        name = m["from_name"] or "?"
        content = m["content"]
        if m["from_user_id"] != for_user_id:
            content = await translate_to(content, target_lang_name)
        lines.append(f"{name}: {content}")
    return header + "\n\n" + "\n".join(lines)


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
        lang = callback.data.replace("lang_", "")
        if lang not in LANGUAGES:
            lang = "other"
        await set_user_language(callback.from_user.id, lang)
        lang_name = LANGUAGES.get(lang, "Other")
        log.info("User %s (%s) chose language", callback.from_user.id, lang_name)
        text = MAIN_MENU_TEXTS.get(lang, MAIN_MENU_TEXTS["other"])
        await callback.message.edit_text(text, reply_markup=main_menu_keyboard(lang))
        await callback.answer()
    except Exception:
        log.exception("on_language failed")


@router.callback_query(F.data == "back_to_menu")
async def on_back_to_menu(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await callback.answer()
        user_id = callback.from_user.id
        bot = callback.bot
        for cid, mid in await view_ads_get_messages(user_id):
            try:
                await bot.delete_message(chat_id=cid, message_id=mid)
            except Exception:
                pass
        await view_ads_clear_messages(user_id)
        lang = await get_user_language(user_id)
        text = MAIN_MENU_TEXTS.get(lang, MAIN_MENU_TEXTS["other"])
        await callback.message.edit_text(text, reply_markup=main_menu_keyboard(lang))
    except Exception:
        log.exception("on_back_to_menu failed")


@router.callback_query(F.data == "post_ad")
async def on_post_ad(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await get_user_language(callback.from_user.id)
    await state.set_state(PostAdStates.waiting_text)
    await state.update_data(lang=lang)
    prompt = ENTER_AD_TEXT.get(lang, ENTER_AD_TEXT["other"])
    await callback.message.edit_text(prompt, reply_markup=cancel_keyboard(lang))


@router.message(PostAdStates.waiting_text, F.text)
async def on_ad_text(message: Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        bot = message.bot
        data = await state.get_data()
        lang = data.get("lang", "other")
        lang_name = LANGUAGES.get(lang, "Other")
        preview = (message.text or "")[:80] + ("..." if len(message.text or "") > 80 else "")
        log.info("User %s (%s) posted ad: %s", user_id, lang_name, preview)
        author_name = message.from_user.full_name or message.from_user.username or str(user_id)
        await save_ad(user_id, lang, message.text, author_name)
        await state.clear()
        confirm = AD_POSTED.get(lang, AD_POSTED["other"])
        menu_text = MAIN_MENU_TEXTS.get(lang, MAIN_MENU_TEXTS["other"])
        text = f"{confirm}\n\n{menu_text}"
        ok = await edit_user_message(bot, user_id, text, main_menu_keyboard(lang))
        if not ok:
            sent = await message.answer(text, reply_markup=main_menu_keyboard(lang))
            await save_user_message(user_id, message.chat.id, sent.message_id)
    except Exception:
        log.exception("on_ad_text failed")


@router.callback_query(F.data == "view_ads")
async def on_view_ads(callback: CallbackQuery):
    try:
        await callback.answer()
        user_id = callback.from_user.id
        lang = await get_user_language(user_id)
        lang_name = LANGUAGES.get(lang, "Other")
        log.info("User %s (%s) viewed ads", user_id, lang_name)
        chat_id = callback.message.chat.id
        bot = callback.bot
        await view_ads_clear_messages(user_id)
        ads = await get_last_ads(limit=VIEW_ADS_MAX, offset=0)
        chat_id_stored, message_id_stored = await get_user_message_ids(user_id)
        if chat_id_stored is not None and message_id_stored is not None and chat_id_stored == chat_id:
            try:
                await bot.delete_message(chat_id=chat_id_stored, message_id=message_id_stored)
            except Exception:
                pass
        if not ads:
            msg = NO_ADS.get(lang, NO_ADS["other"])
            sent = await bot.send_message(chat_id, msg, reply_markup=view_ads_back_keyboard(lang))
            await save_user_message(user_id, chat_id, sent.message_id)
            return
        for ad in ads:
            text = await _build_single_ad_text(ad, lang)
            if len(text) > 4000:
                text = text[:3997] + "..."
            ad_id = int(ad.get("id", 0)) if isinstance(ad, dict) else getattr(ad, "id", 0)
            sent = await bot.send_message(chat_id, text, reply_markup=write_to_author_keyboard(lang, ad_id))
            await view_ads_add_message(user_id, chat_id, sent.message_id)
        back_msg = await bot.send_message(chat_id, "—", reply_markup=view_ads_back_keyboard(lang))
        await save_user_message(user_id, chat_id, back_msg.message_id)
    except Exception:
        log.exception("on_view_ads failed")


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
        # TODO: re-enable for production — block replying to own ad
        # if int(ad.get("user_id", 0)) == callback.from_user.id:
        #     return
        viewer_id = callback.from_user.id
        author_id = int(ad["user_id"])
        viewer_name = callback.from_user.first_name or callback.from_user.username or "Someone"
        log.info("User %s tapped Write to author: viewer=%s, author=%s, ad_id=%s", viewer_id, viewer_id, author_id, ad_id)
        chat_id = callback.message.chat.id
        bot = callback.bot
        lang_viewer = await get_user_language(viewer_id)
        connecting_t = CONNECTING_TEXTS.get(lang_viewer, CONNECTING_TEXTS["other"])
        connecting_msg = await bot.send_message(chat_id, connecting_t)
        session_id = await relay_create(viewer_id, author_id, ad_id)
        log.info("Relay session started: session_id=%s, user_a=%s, user_b=%s, ad_id=%s", session_id, viewer_id, author_id, ad_id)
        lang_author = await get_user_language(author_id)
        interested_t = RELAY_INTERESTED_TEXTS.get(lang_author, RELAY_INTERESTED_TEXTS["other"])
        reply_btn = RELAY_REPLY_BTN_TEXTS.get(lang_author, RELAY_REPLY_BTN_TEXTS["other"])
        ad_preview = (ad.get("content") or "")[:500]
        if len(ad.get("content") or "") > 500:
            ad_preview += "..."
        author_notify = f"{viewer_name} is interested in your ad:\n\n{ad_preview}"
        author_chat_id = await get_user_chat_id(author_id)
        if author_chat_id:
            await bot.send_message(
                author_chat_id,
                author_notify,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text=reply_btn, callback_data=f"relay_reply_{session_id}")]]
                ),
            )
        header = RELAY_CHAT_HEADER_TEXTS.get(lang_viewer, RELAY_CHAT_HEADER_TEXTS["other"])
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=connecting_msg.message_id,
                text=header + "\n\n",
                reply_markup=relay_keyboard(lang_viewer, session_id),
            )
        except Exception as edit_err:
            log.debug("edit_message_text failed: %s", edit_err)
        await save_user_message(viewer_id, chat_id, connecting_msg.message_id)
    except Exception:
        log.exception("reply_ad failed")


@router.callback_query(F.data.startswith("relay_reply_"))
async def on_relay_reply(callback: CallbackQuery):
    try:
        await callback.answer()
        try:
            session_id = int(callback.data.replace("relay_reply_", ""))
        except ValueError:
            return
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, user_a, user_b FROM relay_sessions WHERE id = ?", (session_id,)
            ) as cur:
                row = await cur.fetchone()
                if not row or row["user_b"] != callback.from_user.id:
                    return
        log.info("User %s joined relay session_id=%s", callback.from_user.id, session_id)
        try:
            await callback.message.delete()
        except Exception:
            pass
        lang = await get_user_language(callback.from_user.id)
        text = await _build_relay_ui_text(session_id, callback.from_user.id, lang)
        if len(text) > 4000:
            text = text[:3997] + "..."
        await edit_user_message(callback.bot, callback.from_user.id, text, relay_keyboard(lang, session_id))
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
        session = await relay_get_active_for_user(callback.from_user.id)
        if not session or int(session.get("id", 0)) != session_id:
            return
        user_a_id = int(session["user_a"])
        user_b_id = int(session["user_b"])
        log.info("Relay session ended: session_id=%s, user_a=%s, user_b=%s", session_id, user_a_id, user_b_id)
        bot = callback.bot
        await relay_close(session_id)
        for uid in (user_a_id, user_b_id):
            lang = await get_user_language(uid)
            menu_text = MAIN_MENU_TEXTS.get(lang, MAIN_MENU_TEXTS["other"])
            await edit_user_message(bot, uid, menu_text, main_menu_keyboard(lang))
    except Exception:
        log.exception("on_relay_stop failed")


@router.message(F.text)
async def on_message_relay(message: Message):
    try:
        user_id = message.from_user.id
        session = await relay_get_active_for_user(user_id)
        if not session:
            return
        bot = message.bot
        other_id = await relay_get_other_user(session, user_id)
        from_name = message.from_user.first_name or message.from_user.username or str(user_id)
        original = message.text or ""
        await relay_add_message(session["id"], user_id, from_name, original)
        other_lang = await get_user_language(other_id)
        other_lang_name = LANGUAGES.get(other_lang, "Other")
        translated = await translate_to(original, other_lang_name)
        orig_preview = original[:60] + ("..." if len(original) > 60 else "")
        trans_preview = translated[:60] + ("..." if len(translated) > 60 else "")
        log.info("Relay message forwarded: from=%s to=%s, original=%s, translated=%s", user_id, other_id, orig_preview, trans_preview)
        my_lang = await get_user_language(user_id)
        text_for_me = await _build_relay_ui_text(session["id"], user_id, my_lang)
        text_for_other = await _build_relay_ui_text(session["id"], other_id, other_lang)
        if len(text_for_me) > 4000:
            text_for_me = text_for_me[:3997] + "..."
        if len(text_for_other) > 4000:
            text_for_other = text_for_other[:3997] + "..."
        kb_me = relay_keyboard(my_lang, session["id"])
        kb_other = relay_keyboard(other_lang, session["id"])
        await edit_user_message(bot, user_id, text_for_me, kb_me)
        await edit_user_message(bot, other_id, text_for_other, kb_other)
    except Exception:
        log.exception("on_message_relay failed")
