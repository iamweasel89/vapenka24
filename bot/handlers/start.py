import asyncio
from collections import defaultdict
from datetime import datetime, timezone

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from bot.config import LANGUAGES, ADMIN_USER_ID
from bot.db import get_pool
from bot.logging_config import get_logger
from bot.translate import translate_to, classify_ad_type, moderate_content

log = get_logger()

router = Router()

MAIN_MENU_TEXTS = {
    "sk": "Hlavné menu",
    "uz": "Asosiy menyu",
    "tl": "Pangunahing menu",
    "uk": "Головне меню",
    "ro": "Meniu principal",
    "en": "Main menu",
    "hu": "Főmenü",
}

POST_AD_TEXTS = {
    "sk": "Pridať inzerát",
    "uz": "E'lon joylash",
    "tl": "Mag-post ng ad",
    "uk": "Опублікувати оголошення",
    "ro": "Publică anunț",
    "en": "Post ad",
    "hu": "Hirdetés feladása",
}

VIEW_ADS_TEXTS = {
    "sk": "Prezerať inzeráty",
    "uz": "E'lonlarni ko'rish",
    "tl": "Tingnan ang mga ad",
    "uk": "Переглянути оголошення",
    "ro": "Vezi anunțurile",
    "en": "View ads",
    "hu": "Hirdetések megtekintése",
}

MY_CHATS_TEXTS = {
    "sk": "Moje chaty",
    "uz": "Mening chatlarim",
    "tl": "Aking mga chat",
    "uk": "Мої чати",
    "ro": "Conversațiile mele",
    "en": "My chats",
    "hu": "Chatjeim",
}

NO_CHATS_TEXTS = {
    "sk": "Zatiaľ žiadne aktívne chaty.",
    "uz": "Hozircha faol chatlar yo'q.",
    "tl": "Walang aktibong mga chat pa.",
    "uk": "Поки немає активних чатів.",
    "ro": "Nicio conversație activă încă.",
    "en": "No active chats yet.",
    "hu": "Még nincs aktív csevegés.",
}

BACK_TO_CHATS_TEXTS = {
    "sk": "🔙 Späť na chaty",
    "uz": "🔙 Chatlarga qaytish",
    "tl": "🔙 Bumalik sa mga chat",
    "uk": "🔙 Назад до чатів",
    "ro": "🔙 Înapoi la chat",
    "en": "🔙 Back to chats",
    "hu": "🔙 Vissza a chathez",
}

# Ad type labels for confirmation and view ads — all LANGUAGES keys (sk, uz, tl, uk, ro, en, hu)
TYPE_LABEL_SELL = {"sk": "Predám", "uz": "Sotaman", "tl": "Selling", "uk": "Продаю", "ro": "Vând", "en": "Selling", "hu": "Eladó"}
TYPE_LABEL_SEEK = {"sk": "Hľadám", "uz": "Qidiyman", "tl": "Looking for", "uk": "Шукаю", "ro": "Caut", "en": "Looking for", "hu": "Keresek"}
TYPE_LABEL_GIVE = {"sk": "Dávam", "uz": "Bepul beraman", "tl": "Giving away", "uk": "Віддаю", "ro": "Dau gratuit", "en": "Giving away", "hu": "Ingyen adok"}
TYPE_LABEL_OTHER = {"sk": "Iné", "uz": "Boshqa", "tl": "Other", "uk": "Інше", "ro": "Altele", "en": "Other", "hu": "Egyéb"}
TYPE_LABELS = {"SELL": TYPE_LABEL_SELL, "SEEK": TYPE_LABEL_SEEK, "GIVE": TYPE_LABEL_GIVE, "OTHER": TYPE_LABEL_OTHER}

CONFIRM_TYPE_CORRECT = {"sk": "✅ Správne", "uz": "✅ To'g'ri", "tl": "✅ Correct", "uk": "✅ Правильно", "ro": "✅ Corect", "en": "✅ Correct", "hu": "✅ Helyes"}
CONFIRM_TYPE_CHANGE = {"sk": "✏️ Zmeniť typ", "uz": "✏️ Turini o'zgartirish", "tl": "✏️ Change type", "uk": "✏️ Змінити тип", "ro": "✏️ Schimbă tipul", "en": "✏️ Change type", "hu": "✏️ Típus módosítása"}

FILTER_BTN_TEXTS = {"sk": "🔽 Filter", "uz": "🔽 Filtr", "tl": "🔽 Filter", "uk": "🔽 Фільтр", "ro": "🔽 Filtru", "en": "🔽 Filter", "hu": "🔽 Szűrő"}
FILTER_ALL_TEXTS = {"sk": "Všetko", "uz": "Hammasi", "tl": "All", "uk": "Все", "ro": "Toate", "en": "All", "hu": "Összes"}

ENTER_AD_TEXT = {
    "sk": "Zadajte text inzerátu:",
    "uz": "E'lon matnini kiriting:",
    "tl": "Ilagay ang teksto ng ad:",
    "uk": "Введіть текст оголошення:",
    "ro": "Introdu textul anunțului:",
    "en": "Enter ad text:",
    "hu": "Add meg a hirdetés szövegét:",
}

AD_POSTED = {
    "sk": "Inzerát bol uverejnený!",
    "uz": "E'lon joylandi!",
    "tl": "Na-post na ang ad!",
    "uk": "Оголошення опубліковано!",
    "ro": "Anunț publicat!",
    "en": "Ad posted!",
    "hu": "Hirdetés közzétéve!",
}

NO_ADS = {
    "sk": "Zatiaľ žiadne inzeráty.",
    "uz": "Hozircha e'lonlar yo'q.",
    "tl": "Walang mga ad pa.",
    "uk": "Поки немає оголошень.",
    "ro": "Nicio anunț încă.",
    "en": "No ads yet.",
    "hu": "Még nincsenek hirdetések.",
}

BACK_TEXTS = {
    "sk": "← Späť",
    "uz": "← Orqaga",
    "tl": "← Bumalik",
    "uk": "← Назад",
    "ro": "← Înapoi",
    "en": "← Back",
    "hu": "← Vissza",
}

CANCEL_TEXTS = {
    "sk": "Zrušiť",
    "uz": "Bekor qilish",
    "tl": "Kanselahin",
    "uk": "Скасувати",
    "ro": "Anulare",
    "en": "Cancel",
    "hu": "Mégse",
}

ADD_PHOTO_PROMPT = {
    "sk": "Pridať fotku? (voliteľné)",
    "uz": "Foto qo'shasizmi? (ixtiyoriy)",
    "tl": "Magdagdag ng larawan? (opsyonal)",
    "uk": "Додати фото? (необов'язково)",
    "ro": "Adaugi o poză? (opțional)",
    "en": "Add a photo? (optional)",
    "hu": "Fénykép hozzáadása? (opcionális)",
}
ADD_PHOTO_BTN = {"sk": "📷 Pridať fotku", "uz": "📷 Foto qo'shish", "tl": "📷 Magdagdag ng larawan", "uk": "📷 Додати фото", "ro": "📷 Adaugă poză", "en": "📷 Add photo", "hu": "📷 Fénykép hozzáadása"}
SKIP_PHOTO_BTN = {"sk": "⏭️ Preskočiť", "uz": "⏭️ O'tkazish", "tl": "⏭️ Laktawan", "uk": "⏭️ Пропустити", "ro": "⏭️ Omite", "en": "⏭️ Skip", "hu": "⏭️ Kihagyás"}
SEND_PHOTO_NOW = {"sk": "Pošlite fotku.", "uz": "Fotoni yuboring.", "tl": "Magpadala ng larawan.", "uk": "Надішліть фото.", "ro": "Trimite fotografia.", "en": "Send your photo now.", "hu": "Küldd el a fényképet."}

WRITE_TO_AUTHOR_TEXTS = {
    "sk": "✉️ Napísať autorovi",
    "uz": "✉️ Muallifga yozish",
    "tl": "✉️ Sumulat sa may-akda",
    "uk": "✉️ Написати автору",
    "ro": "✉️ Scrie autorului",
    "en": "✉️ Write to author",
    "hu": "✉️ Írás a szerzőnek",
}

BACK_EMOJI_TEXTS = {"sk": "🔙 Späť", "uz": "🔙 Orqaga", "tl": "🔙 Bumalik", "uk": "🔙 Назад", "ro": "🔙 Înapoi", "en": "🔙 Back", "hu": "🔙 Vissza"}

RELAY_INTERESTED_TEXTS = {
    "sk": "Niekto má záujem o váš inzerát:",
    "uz": "Kimdir sizning e'loningizga qiziqyapti:",
    "tl": "May interesado sa iyong ad:",
    "uk": "Хтось зацікавлений у вашому оголошенні:",
    "ro": "Cineva e interesat de anunțul tău:",
    "en": "Someone is interested in your ad:",
    "hu": "Valaki érdeklődik a hirdetésed iránt:",
}

def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    try:
        return {k: row[k] for k in row.keys()}
    except Exception:
        return dict(row) if row else None
RELAY_REPLY_BTN_TEXTS = {"sk": "✉️ Odpovedať", "uz": "✉️ Javob berish", "tl": "✉️ Sumagot", "uk": "✉️ Відповісти", "ro": "✉️ Răspunde", "en": "✉️ Reply", "hu": "✉️ Válasz"}
RELAY_CHAT_HEADER_TEXTS = {
    "sk": "Chat k inzerátu. Napíšte správu:",
    "uz": "E'lon bo'yicha chat. Xabar yozing:",
    "tl": "Chat tungkol sa ad. Mag-type ng mensahe:",
    "uk": "Чат щодо оголошення. Напишіть повідомлення:",
    "ro": "Chat despre anunț. Scrie mesajul:",
    "en": "Chat about your ad. Type your message:",
    "hu": "Chat a hirdetésedről. Írd be az üzenetet:",
}
RELAY_STOP_TEXTS = {"sk": "🔙 Ukončiť chat", "uz": "🔙 Chatni tugatish", "tl": "🔙 I-stop ang chat", "uk": "🔙 Зупинити чат", "ro": "🔙 Încheie chat", "en": "🔙 End chat", "hu": "🔙 Chat befejezése"}

RELAY_HEADER_CHAT_WITH = {"sk": "💬 Chat s", "uz": "💬 Chat", "tl": "💬 Chat sa", "uk": "💬 Чат з", "ro": "💬 Chat cu", "en": "💬 Chat with", "hu": "💬 Chat"}
RELAY_HEADER_ABOUT = {"sk": "O inzeráte:", "uz": "E'lon:", "tl": "Tungkol sa:", "uk": "Про оголошення:", "ro": "Despre anunț:", "en": "About:", "hu": "A hirdetésről:"}
RELAY_HEADER_TYPE_BELOW = {"sk": "Napíšte správu nižšie:", "uz": "Xabar yozing:", "tl": "Mag-type ng mensahe sa ibaba:", "uk": "Напишіть повідомлення нижче:", "ro": "Scrie mesajul mai jos:", "en": "Type your message below:", "hu": "Írd be az üzenetet alább:"}

CONNECTING_TEXTS = {
    "sk": "Pripájam vás s autorom...",
    "uz": "Sizni muallif bilan bog'layapmiz...",
    "tl": "Ikino-connect ka sa may-akda...",
    "uk": "З'єдную з автором...",
    "ro": "Te conectez cu autorul...",
    "en": "Connecting you with the author...",
    "hu": "Kapcsolás a szerzővel...",
}

NEW_MESSAGE_FROM_TEXTS = {
    "sk": "💬 Nová správa od",
    "uz": "💬 Yangi xabar",
    "tl": "💬 Bagong mensahe mula sa",
    "uk": "💬 Нове повідомлення від",
    "ro": "💬 Mesaj nou de la",
    "en": "💬 New message from",
    "hu": "💬 Új üzenet",
}
OPEN_CHAT_BTN_TEXTS = {
    "sk": "Otvorit chat",
    "uz": "Chatni ochish",
    "tl": "Buksan ang chat",
    "uk": "Відкрити чат",
    "ro": "Deschide chat",
    "en": "Open chat",
    "hu": "Chat megnyitása",
}

FEEDBACK_BTN_TEXTS = {
    "sk": "💬 Spätná väzba",
    "uz": "💬 Fikr-mulohaza",
    "tl": "💬 Feedback",
    "uk": "💬 Зворотний зв'язок",
    "ro": "💬 Feedback",
    "en": "💬 Feedback",
    "hu": "💬 Visszajelzés",
}
FEEDBACK_PROMPT_TEXTS = {
    "sk": "Napíšte svoju spätnú väzbu (vo svojom jazyku):",
    "uz": "Fikr-mulohazangizni yozing (o'z tilingizda):",
    "tl": "Isulat ang iyong feedback (sa iyong wika):",
    "uk": "Напишіть свій відгук (своєю мовою):",
    "ro": "Scrie feedback-ul tău (în limba ta):",
    "en": "Write your feedback (in your language):",
    "hu": "Írja meg visszajelzését (a saját nyelvén):",
}

RULES_TEXTS = {
    "sk": "Pár pravidiel: uverejňujte len inzeráty na predmet a služby. Žiadne urážky ani agresia. Žiadny spam ani reklama zvonku. Porušenia znamenajú ban.",
    "uz": "Bir necha qoida: faqat buyumlar va xizmatlar haqida e'lonlar joylang. Haqorat yoki tajovuz yo'q. Spam yoki tashqi reklama yo'q. Bu buzilishlar ban bilan yakunlanadi.",
    "tl": "Ilang patakaran: mag-post lamang ng mga ad tungkol sa mga item at serbisyo. Walang insulto o agresyon. Walang spam o labas na advertising. Ang mga paglabag ay nagresulta sa ban.",
    "uk": "Кілька правил: публікуйте лише оголошення про речі та послуги. Без образ і агресії. Без спаму та зовнішньої реклами. Порушення призводять до бану.",
    "ro": "Câteva reguli: postați doar anunțuri despre obiecte și servicii. Fără insulte sau agresivitate. Fără spam sau reclame externe. Încălcările duc la ban.",
    "en": "A few rules: post only ads about items and services. No insults or aggression. No spam or outside advertising. Violations result in a ban.",
    "hu": "Néhány szabály: csak tárgyakról és szolgáltatásokról szóló hirdetéseket tegyél közzé. Nincs sértés vagy agresszió. Nincs spam vagy külső reklám. A szabálysértések bant eredményeznek.",
}
I_UNDERSTAND_TEXTS = {
    "sk": "✅ Rozumiem",
    "uz": "✅ Tushundim",
    "tl": "✅ Naiintindihan ko",
    "uk": "✅ Я розумію",
    "ro": "✅ Înțeleg",
    "en": "✅ I understand",
    "hu": "✅ Értem",
}
BLOCKED_TEXTS = {
    "sk": "Váš účet bol zablokovaný. Obráťte sa na administrátora.",
    "uz": "Hisobingiz bloklangan. Administrator bilan bog'laning.",
    "tl": "Na-block ang iyong account. Makipag-ugnayan sa administrator.",
    "uk": "Ваш обліковий запис заблоковано. Зв'яжіться з адміністратором.",
    "ro": "Contul dvs. a fost blocat. Contactați administratorul.",
    "en": "Your account has been blocked. Contact the administrator.",
    "hu": "A fiókodat blokkolták. Lépj kapcsolatba az adminisztrátorral.",
}

CHOOSE_LANG_TEXT = "Choose language / Vyberte jazyk / Tilni tanlang / Pumili ng wika / Оберіть мову / Alegeți limba / Válasszon nyelvet:"

WELCOME_MESSAGE_EN = (
    "Vápenka 24 — a bulletin board for residents of this building. "
    "You can sell things, find a neighbor, or give something away for free — all in your language."
)
WELCOME_MESSAGE_UK = (
    "Вапенка 24 — дошка оголошень для мешканців цього будинку. "
    "Продавай, шукай, віддавай — і все своєю мовою."
)

LANG_BUTTON_TEXTS = {
    "sk": "🇸🇰 Slovak",
    "uz": "🇺🇿 Uzbek",
    "tl": "🇵🇭 Tagalog",
    "uk": "🇺🇦 Ukrainian",
    "ro": "🇷🇴 Romanian",
    "en": "🇬🇧 English",
    "hu": "🇭🇺 Hungarian",
}


def _days_left(expires_at: str | datetime | None) -> str:
    if expires_at is None:
        return "? days left"
    try:
        # PostgreSQL/asyncpg returns datetime; SQLite or strings come as str
        if isinstance(expires_at, datetime):
            end = expires_at
        else:
            # String: "YYYY-MM-DD HH:MM:SS" or ISO with Z
            end = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = (end - now).days
        if delta < 0:
            return "0 days left"
        if delta == 1:
            return "1 day left"
        return f"{delta} days left"
    except (ValueError, TypeError, AttributeError):
        return "? days left"


def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=LANG_BUTTON_TEXTS.get(code, name), callback_data=f"lang_{code}")]
            for code, name in LANGUAGES.items()
        ]
    )


def main_menu_keyboard(lang: str, user_id: int | None = None) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=POST_AD_TEXTS.get(lang, POST_AD_TEXTS["en"]), callback_data="post_ad")],
        [InlineKeyboardButton(text=VIEW_ADS_TEXTS.get(lang, VIEW_ADS_TEXTS["en"]), callback_data="view_ads")],
        [InlineKeyboardButton(text=MY_CHATS_TEXTS.get(lang, MY_CHATS_TEXTS["en"]), callback_data="my_chats")],
        [InlineKeyboardButton(text=FEEDBACK_BTN_TEXTS.get(lang, FEEDBACK_BTN_TEXTS["en"]), callback_data="feedback")],
    ]
    if user_id is not None and ADMIN_USER_ID is not None and user_id == ADMIN_USER_ID:
        rows.append([InlineKeyboardButton(text="⚙️ Admin", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BACK_TEXTS.get(lang, BACK_TEXTS["en"]), callback_data="back_to_menu")]
        ]
    )


def cancel_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=CANCEL_TEXTS[lang], callback_data="back_to_menu")]
        ]
    )


async def save_user_message(user_id: int, chat_id: int, message_id: int):
    async with get_pool().acquire() as conn:
        await conn.execute(
            """INSERT INTO users (user_id, language, chat_id, message_id) VALUES ($1, 'en', $2, $3)
               ON CONFLICT(user_id) DO UPDATE SET chat_id = EXCLUDED.chat_id, message_id = EXCLUDED.message_id""",
            user_id, chat_id, message_id,
        )


async def get_user_message_ids(user_id: int) -> tuple[int | None, int | None]:
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT chat_id, message_id FROM users WHERE user_id = $1", user_id,
        )
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
    """Return user's language code (sk, uk, en, etc.). Always returns a key from LANGUAGES."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT language FROM users WHERE user_id = $1", user_id,
        )
        if not row or row["language"] is None:
            return "en"
        raw = str(row["language"]).strip().lower()
        return raw if raw in LANGUAGES else "en"


USER_STATE_MAIN_MENU = "MAIN_MENU"
USER_STATE_VIEWING_ADS = "VIEWING_ADS"
USER_STATE_POSTING_AD = "POSTING_AD"
USER_STATE_POSTING_AD_PHOTO = "POSTING_AD_PHOTO"
USER_STATE_MY_CHATS = "MY_CHATS"
USER_STATE_IN_RELAY = "IN_RELAY"
USER_STATE_ADMIN_MENU = "ADMIN_MENU"
USER_STATE_FEEDBACK = "FEEDBACK"


async def get_user_state(user_id: int) -> str:
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT state FROM users WHERE user_id = $1", user_id,
        )
        if row and row["state"]:
            return str(row["state"])
        return USER_STATE_MAIN_MENU


async def set_user_state_db(user_id: int, state: str):
    async with get_pool().acquire() as conn:
        await conn.execute(
            """INSERT INTO users (user_id, state) VALUES ($1, $2)
               ON CONFLICT(user_id) DO UPDATE SET state = EXCLUDED.state""",
            user_id, state,
        )


async def get_user_current_relay_id(user_id: int) -> int | None:
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT current_relay_id FROM users WHERE user_id = $1", user_id,
        )
        if row and row["current_relay_id"] is not None:
            return int(row["current_relay_id"])
        return None


async def set_user_current_relay_id(user_id: int, session_id: int | None):
    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE users SET current_relay_id = $1 WHERE user_id = $2",
            session_id, user_id,
        )


async def set_user_language(user_id: int, lang: str):
    async with get_pool().acquire() as conn:
        await conn.execute(
            """INSERT INTO users (user_id, language) VALUES ($1, $2)
               ON CONFLICT(user_id) DO UPDATE SET language = EXCLUDED.language""",
            user_id, lang,
        )


async def get_user_welcome_shown(user_id: int) -> bool:
    """True if we have already shown the one-time welcome (or legacy user with no flag)."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT welcome_shown FROM users WHERE user_id = $1", user_id,
        )
        if row is None:
            return False
        val = row["welcome_shown"]
        if val is None:
            return True
        return int(val) == 1


async def set_user_welcome_shown(user_id: int, shown: bool = True) -> None:
    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE users SET welcome_shown = $1 WHERE user_id = $2",
            1 if shown else 0, user_id,
        )


async def get_user_rules_accepted(user_id: int) -> bool:
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT rules_accepted FROM users WHERE user_id = $1", user_id,
        )
        if row is None:
            return False
        val = row.get("rules_accepted") if hasattr(row, "get") else row["rules_accepted"]
        return val is not None and int(val) == 1


async def set_user_rules_accepted(user_id: int, accepted: bool = True) -> None:
    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE users SET rules_accepted = $1 WHERE user_id = $2",
            1 if accepted else 0, user_id,
        )


async def get_user_banned(user_id: int) -> bool:
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT is_banned FROM users WHERE user_id = $1", user_id,
        )
        if row is None:
            return False
        val = row.get("is_banned") if hasattr(row, "get") else row["is_banned"]
        return bool(val)


async def set_user_banned(user_id: int, banned: bool) -> None:
    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_banned = $1 WHERE user_id = $2",
            banned, user_id,
        )


async def save_ad(user_id: int, language: str, text: str, author_name: str, ad_type: str = "OTHER") -> int:
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO ads (user_id, language, content, author_name, type)
               VALUES ($1, $2, $3, $4, $5) RETURNING id""",
            user_id, language, text, author_name, ad_type,
        )
        return row["id"]


async def update_ad_type(ad_id: int, ad_type: str):
    async with get_pool().acquire() as conn:
        await conn.execute("UPDATE ads SET type = $1 WHERE id = $2", ad_type, ad_id)


async def update_ad_photo(ad_id: int, photo_id: str) -> None:
    async with get_pool().acquire() as conn:
        await conn.execute("UPDATE ads SET photo_id = $1 WHERE id = $2", photo_id, ad_id)


async def get_user_pending_ad_id(user_id: int) -> int | None:
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT pending_ad_id FROM users WHERE user_id = $1", user_id,
        )
        if row and row["pending_ad_id"] is not None:
            return int(row["pending_ad_id"])
        return None


async def set_user_pending_ad_id(user_id: int, ad_id: int | None) -> None:
    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE users SET pending_ad_id = $1 WHERE user_id = $2",
            ad_id, user_id,
        )


async def get_ads_count(type_filter: str | None = None) -> int:
    async with get_pool().acquire() as conn:
        if type_filter and type_filter != "ALL":
            row = await conn.fetchrow(
                "SELECT COUNT(*) FROM ads WHERE expires_at > CURRENT_TIMESTAMP AND type = $1",
                type_filter,
            )
        else:
            row = await conn.fetchrow(
                "SELECT COUNT(*) FROM ads WHERE expires_at > CURRENT_TIMESTAMP",
            )
        return row[0] if row else 0


async def get_last_ads(limit: int = 10, offset: int = 0, type_filter: str | None = None):
    async with get_pool().acquire() as conn:
        if type_filter and type_filter != "ALL":
            rows = await conn.fetch(
                """SELECT id, user_id, language, content, author_name, type, created_at, expires_at, photo_id
                   FROM ads WHERE expires_at > CURRENT_TIMESTAMP AND type = $1
                   ORDER BY created_at DESC LIMIT $2 OFFSET $3""",
                type_filter, limit, offset,
            )
        else:
            rows = await conn.fetch(
                """SELECT id, user_id, language, content, author_name, type, created_at, expires_at, photo_id
                   FROM ads WHERE expires_at > CURRENT_TIMESTAMP
                   ORDER BY created_at DESC LIMIT $1 OFFSET $2""",
                limit, offset,
            )
        return [_row_to_dict(row) or dict(row) for row in rows]


async def get_ad_by_id(ad_id: int):
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, user_id, language, content, author_name, type, photo_id FROM ads WHERE id = $1",
            ad_id,
        )
        return _row_to_dict(row) if row else None


async def get_user_view_ads_filter(user_id: int) -> str:
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT view_ads_filter FROM users WHERE user_id = $1", user_id,
        )
        if row and row["view_ads_filter"]:
            return str(row["view_ads_filter"])
        return "ALL"


async def set_user_view_ads_filter(user_id: int, value: str):
    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE users SET view_ads_filter = $1 WHERE user_id = $2",
            value, user_id,
        )


async def get_all_users() -> list:
    """All registered users for admin list. Each dict has user_id, language, created_at, is_banned."""
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, language, created_at, COALESCE(is_banned, false) AS is_banned FROM users ORDER BY user_id",
        )
        return [_row_to_dict(row) or dict(row) for row in rows]


async def get_banned_users() -> list:
    """Users with is_banned = true for admin banned list."""
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, language, created_at FROM users WHERE is_banned = true ORDER BY user_id",
        )
        return [_row_to_dict(row) or dict(row) for row in rows]


async def get_all_active_ads_admin() -> list:
    """All active ads for admin list (expires_at > now)."""
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, user_id, author_name, type, content, expires_at
               FROM ads WHERE expires_at > CURRENT_TIMESTAMP ORDER BY id DESC""",
        )
        return [_row_to_dict(row) or dict(row) for row in rows]


async def admin_delete_ad(ad_id: int):
    """Delete one ad and its relay sessions/messages."""
    async with get_pool().acquire() as conn:
        await conn.execute(
            "DELETE FROM relay_messages WHERE relay_id IN (SELECT id FROM relay_sessions WHERE ad_id = $1)",
            ad_id,
        )
        await conn.execute("DELETE FROM relay_sessions WHERE ad_id = $1", ad_id)
        await conn.execute("DELETE FROM ads WHERE id = $1", ad_id)


async def insert_suspicious_ad(ad_id: int) -> None:
    """Record a suspicious ad for admin review (status=pending)."""
    async with get_pool().acquire() as conn:
        await conn.execute(
            """INSERT INTO suspicious_ads (ad_id, notified_at, status) VALUES ($1, CURRENT_TIMESTAMP, 'pending')
               ON CONFLICT (ad_id) DO UPDATE SET notified_at = CURRENT_TIMESTAMP, status = 'pending'""",
            ad_id,
        )


async def get_pending_suspicious_count() -> int:
    """Count of suspicious ads with status=pending."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) FROM suspicious_ads WHERE status = 'pending'",
        )
        return row[0] if row else 0


async def get_pending_suspicious_ads() -> list:
    """Pending suspicious ads with ad content (join ads). Returns list of dicts with ad_id, content, notified_at."""
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            """SELECT s.ad_id, s.notified_at, a.content
               FROM suspicious_ads s
               JOIN ads a ON a.id = s.ad_id
               WHERE s.status = 'pending'
               ORDER BY s.notified_at ASC""",
        )
        return [_row_to_dict(row) or dict(row) for row in rows]


async def update_suspicious_status(ad_id: int, status: str) -> None:
    """Set status for a suspicious ad: pending, kept, or removed."""
    if status not in ("pending", "kept", "removed"):
        return
    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE suspicious_ads SET status = $1 WHERE ad_id = $2",
            status, ad_id,
        )


async def update_suspicious_notification(ad_id: int, chat_id: int, message_id: int) -> None:
    """Store the admin push notification message so we can delete it after review."""
    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE suspicious_ads SET notification_chat_id = $1, notification_message_id = $2 WHERE ad_id = $3",
            chat_id, message_id, ad_id,
        )


async def get_suspicious_notification(ad_id: int) -> tuple[int | None, int | None]:
    """Return (chat_id, message_id) for the admin notification message, or (None, None)."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT notification_chat_id, notification_message_id FROM suspicious_ads WHERE ad_id = $1",
            ad_id,
        )
        if not row or row["notification_chat_id"] is None or row["notification_message_id"] is None:
            return None, None
        return int(row["notification_chat_id"]), int(row["notification_message_id"])


async def admin_clear_ads_and_relays():
    """Delete all ads, relay data, and suspicious_ads; keep users."""
    async with get_pool().acquire() as conn:
        await conn.execute("DELETE FROM relay_messages")
        await conn.execute("DELETE FROM relay_sessions")
        await conn.execute("DELETE FROM suspicious_ads")
        await conn.execute("DELETE FROM ads")


async def admin_delete_user(user_id: int) -> None:
    """Delete a user and all their ads, relay sessions and messages. Caller must be admin."""
    async with get_pool().acquire() as conn:
        await conn.execute(
            "DELETE FROM relay_messages WHERE relay_id IN (SELECT id FROM relay_sessions WHERE user_a = $1 OR user_b = $1)",
            user_id, user_id,
        )
        await conn.execute(
            "DELETE FROM relay_sessions WHERE user_a = $1 OR user_b = $1",
            user_id, user_id,
        )
        await conn.execute(
            "DELETE FROM suspicious_ads WHERE ad_id IN (SELECT id FROM ads WHERE user_id = $1)",
            user_id,
        )
        await conn.execute("DELETE FROM ads WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM view_ads_messages WHERE user_id = $1", user_id)
        await conn.execute("DELETE FROM users WHERE user_id = $1", user_id)


async def count_active_relay_sessions() -> int:
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) FROM relay_sessions WHERE status = 'active'",
        )
        return row[0] if row else 0


async def get_user_chat_id(user_id: int) -> int | None:
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT chat_id FROM users WHERE user_id = $1", user_id,
        )
        return int(row["chat_id"]) if row and row["chat_id"] is not None else None


async def view_ads_clear_messages(user_id: int):
    async with get_pool().acquire() as conn:
        await conn.execute("DELETE FROM view_ads_messages WHERE user_id = $1", user_id)


async def view_ads_add_message(user_id: int, chat_id: int, message_id: int):
    async with get_pool().acquire() as conn:
        await conn.execute(
            "INSERT INTO view_ads_messages (user_id, chat_id, message_id) VALUES ($1, $2, $3)",
            user_id, chat_id, message_id,
        )


async def view_ads_get_messages(user_id: int) -> list[tuple[int, int]]:
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            "SELECT chat_id, message_id FROM view_ads_messages WHERE user_id = $1",
            user_id,
        )
        return [(int(r["chat_id"]), int(r["message_id"])) for r in rows]


def write_to_author_keyboard(lang: str, ad_id: int) -> InlineKeyboardMarkup:
    write_t = WRITE_TO_AUTHOR_TEXTS.get(lang, WRITE_TO_AUTHOR_TEXTS["en"])
    data = f"{CALLBACK_REPLY_AD_PREFIX}{int(ad_id)}"[:64]  # Telegram limit 64 bytes
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=write_t, callback_data=data)]]
    )


def view_ads_back_keyboard(lang: str) -> InlineKeyboardMarkup:
    back_t = BACK_EMOJI_TEXTS.get(lang, BACK_EMOJI_TEXTS["en"])
    filter_t = FILTER_BTN_TEXTS.get(lang, FILTER_BTN_TEXTS["en"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=filter_t, callback_data="view_ads_filter_open"), InlineKeyboardButton(text=back_t, callback_data="back_to_menu")],
        ]
    )


def view_ads_last_ad_keyboard(lang: str, ad_id: int) -> InlineKeyboardMarkup:
    """Keyboard for the last ad: Write to author, Filter, Back."""
    write_t = WRITE_TO_AUTHOR_TEXTS.get(lang, WRITE_TO_AUTHOR_TEXTS["en"])
    back_t = BACK_EMOJI_TEXTS.get(lang, BACK_EMOJI_TEXTS["en"])
    filter_t = FILTER_BTN_TEXTS.get(lang, FILTER_BTN_TEXTS["en"])
    data = f"{CALLBACK_REPLY_AD_PREFIX}{int(ad_id)}"[:64]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=write_t, callback_data=data)],
            [InlineKeyboardButton(text=filter_t, callback_data="view_ads_filter_open"), InlineKeyboardButton(text=back_t, callback_data="back_to_menu")],
        ]
    )


def _ad_type_label(ad_type: str, lang: str) -> str:
    return TYPE_LABELS.get(ad_type or "OTHER", TYPE_LABEL_OTHER).get(lang, TYPE_LABEL_OTHER["en"])


async def _build_single_ad_text(ad: dict, viewer_lang: str, ad_id: int = 0) -> str:
    """Build ad display text. Always translate to VIEWER's language (source language detected by OpenAI)."""
    viewer_lang = (viewer_lang or "en").strip() or "en"
    type_label = _ad_type_label(ad.get("type") or "OTHER", viewer_lang)
    name = ad["author_name"] or "Unknown"
    days_left = _days_left(ad.get("expires_at"))
    content = ad["content"]
    target_language_name = LANGUAGES.get(viewer_lang, "Other")
    content = await translate_to(content, target_language_name)
    return f"🏷 {type_label}\n👤 {name}\n· {days_left}\n\n{content}"


VIEW_ADS_MAX = 30

# Must match exactly: button callback_data and handler filter (max 64 bytes for Telegram)
CALLBACK_REPLY_AD_PREFIX = "reply_ad_"


async def relay_find_active_session(user_a: int, user_b: int, ad_id: int) -> dict | None:
    """Return existing active session between user_a (viewer) and user_b (author) for this ad, or None."""
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, user_a, user_b, ad_id, viewer_name, author_joined, status
               FROM relay_sessions WHERE status = 'active' AND user_a = $1 AND user_b = $2 AND ad_id = $3 LIMIT 1""",
            user_a, user_b, ad_id,
        )
        return _row_to_dict(row) if row else None


async def relay_create(user_a: int, user_b: int, ad_id: int, viewer_name: str = "") -> int:
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO relay_sessions (user_a, user_b, ad_id, viewer_name, status)
               VALUES ($1, $2, $3, $4, 'active') RETURNING id""",
            user_a, user_b, ad_id, viewer_name or "",
        )
        return row["id"]


async def relay_get_active_sessions_for_user(user_id: int) -> list:
    """All active relay sessions where user is participant (user_a or user_b)."""
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, user_a, user_b, ad_id, viewer_name, author_joined, status
               FROM relay_sessions WHERE status = 'active' AND (user_a = $1 OR user_b = $2) ORDER BY id DESC""",
            user_id, user_id,
        )
        return [_row_to_dict(row) or dict(row) for row in rows]


async def relay_get_session_by_id(session_id: int, active_only: bool = True) -> dict | None:
    """Get session by id. If active_only, only return when status='active'."""
    async with get_pool().acquire() as conn:
        if active_only:
            row = await conn.fetchrow(
                """SELECT id, user_a, user_b, ad_id, viewer_name, author_joined, status
                   FROM relay_sessions WHERE id = $1 AND status = 'active'""",
                session_id,
            )
        else:
            row = await conn.fetchrow(
                """SELECT id, user_a, user_b, ad_id, viewer_name, author_joined, status
                   FROM relay_sessions WHERE id = $1""",
                session_id,
            )
        return _row_to_dict(row) if row else None


async def relay_set_author_joined(relay_id: int):
    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE relay_sessions SET author_joined = 1 WHERE id = $1",
            relay_id,
        )


async def relay_get_other_user(session: dict, user_id: int) -> int:
    return session["user_b"] if session["user_a"] == user_id else session["user_a"]


async def relay_add_message(relay_id: int, from_user_id: int, from_name: str, content: str):
    async with get_pool().acquire() as conn:
        await conn.execute(
            "INSERT INTO relay_messages (relay_id, from_user_id, from_name, content) VALUES ($1, $2, $3, $4)",
            relay_id, from_user_id, from_name, content,
        )


async def relay_get_messages(relay_id: int):
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            "SELECT from_user_id, from_name, content FROM relay_messages WHERE relay_id = $1 ORDER BY id",
            relay_id,
        )
        return [_row_to_dict(row) or dict(row) for row in rows]


async def relay_close(relay_id: int):
    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE relay_sessions SET status = 'closed' WHERE id = $1",
            relay_id,
        )


def relay_keyboard(lang: str, session_id: int) -> InlineKeyboardMarkup:
    back_chats_t = BACK_TO_CHATS_TEXTS.get(lang, BACK_TO_CHATS_TEXTS["en"])
    stop_t = RELAY_STOP_TEXTS.get(lang, RELAY_STOP_TEXTS["en"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=back_chats_t, callback_data="back_to_chats")],
            [InlineKeyboardButton(text=stop_t, callback_data=f"relay_stop_{session_id}")],
        ]
    )


def _relay_opening_text(lang: str, other_name: str, ad_preview: str) -> str:
    chat_with = RELAY_HEADER_CHAT_WITH.get(lang, RELAY_HEADER_CHAT_WITH["en"])
    about = RELAY_HEADER_ABOUT.get(lang, RELAY_HEADER_ABOUT["en"])
    type_below = RELAY_HEADER_TYPE_BELOW.get(lang, RELAY_HEADER_TYPE_BELOW["en"])
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
    session = await relay_get_session_by_id(relay_id, active_only=False)
    ad_block = ""
    if session and session.get("ad_id"):
        ad = await get_ad_by_id(int(session["ad_id"]))
        if ad and ad.get("content"):
            ad_content = await translate_to((ad["content"] or "").strip(), target_lang_name)
            ad_block = "📋 " + ad_content + "\n─────────────\n\n"
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
        return ad_block + thread
    header_text = RELAY_CHAT_HEADER_TEXTS.get(lang, RELAY_CHAT_HEADER_TEXTS["en"])
    body = header_text + "\n\n" + thread if thread else header_text + "\n\n"
    return ad_block + body


async def _draw_main_menu(bot: Bot, user_id: int, chat_id: int, *, text: str | None = None, reply_markup=None):
    if await get_user_banned(user_id):
        lang = await get_user_language(user_id)
        blocked_text = BLOCKED_TEXTS.get(lang, BLOCKED_TEXTS["en"])
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="💬 Contact admin", callback_data="feedback")]]
        )
        sent = await bot.send_message(chat_id, blocked_text, reply_markup=kb)
        await save_user_message(user_id, chat_id, sent.message_id)
        return
    lang = await get_user_language(user_id)
    if text is None:
        text = MAIN_MENU_TEXTS.get(lang, MAIN_MENU_TEXTS["en"])
    if reply_markup is None:
        reply_markup = main_menu_keyboard(lang, user_id)
    sent = await bot.send_message(chat_id, text, reply_markup=reply_markup)
    await save_user_message(user_id, chat_id, sent.message_id)


async def _draw_feedback_prompt(bot: Bot, user_id: int, chat_id: int):
    lang = await get_user_language(user_id)
    prompt = FEEDBACK_PROMPT_TEXTS.get(lang, FEEDBACK_PROMPT_TEXTS["en"])
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=BACK_TEXTS.get(lang, BACK_TEXTS["en"]), callback_data="back_to_menu")]]
    )
    sent = await bot.send_message(chat_id, prompt, reply_markup=kb)
    await save_user_message(user_id, chat_id, sent.message_id)


async def _draw_viewing_ads(bot: Bot, user_id: int, chat_id: int):
    viewer_lang = await get_user_language(user_id)
    loading_text = await translate_to("⏳ Loading...", LANGUAGES.get(viewer_lang, "Other"))
    loading_msg = await bot.send_message(chat_id, loading_text)
    await view_ads_add_message(user_id, chat_id, loading_msg.message_id)

    type_filter = await get_user_view_ads_filter(user_id)
    ads = await get_last_ads(limit=VIEW_ADS_MAX, offset=0, type_filter=type_filter)

    for cid, mid in await view_ads_get_messages(user_id):
        try:
            await bot.delete_message(chat_id=cid, message_id=mid)
        except Exception:
            pass
    await view_ads_clear_messages(user_id)

    if not ads:
        msg = NO_ADS.get(viewer_lang, NO_ADS["en"])
        sent = await bot.send_message(chat_id, msg, reply_markup=view_ads_back_keyboard(viewer_lang))
        await save_user_message(user_id, chat_id, sent.message_id)
        return
    # Translate all ads in parallel
    tasks = [
        _build_single_ad_text(ad, viewer_lang, int(ad.get("id", 0)) if isinstance(ad, dict) else getattr(ad, "id", 0))
        for ad in ads
    ]
    texts = await asyncio.gather(*tasks)
    for i, (ad, text) in enumerate(zip(ads, texts)):
        if len(text) > 4000:
            text = text[:3997] + "..."
        ad_id = int(ad.get("id", 0)) if isinstance(ad, dict) else getattr(ad, "id", 0)
        is_last = i == len(ads) - 1
        kb = view_ads_last_ad_keyboard(viewer_lang, ad_id) if is_last else write_to_author_keyboard(viewer_lang, ad_id)
        photo_id = ad.get("photo_id") if isinstance(ad, dict) else getattr(ad, "photo_id", None)
        if photo_id and str(photo_id).strip():
            caption = text[:1024] if len(text) > 1024 else text
            sent = await bot.send_photo(chat_id, photo=photo_id, caption=caption, reply_markup=kb)
        else:
            sent = await bot.send_message(chat_id, text, reply_markup=kb)
        await view_ads_add_message(user_id, chat_id, sent.message_id)
        if is_last:
            await save_user_message(user_id, chat_id, sent.message_id)


async def _draw_posting_ad(bot: Bot, user_id: int, chat_id: int):
    lang = await get_user_language(user_id)
    prompt = ENTER_AD_TEXT.get(lang, ENTER_AD_TEXT["en"])
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
        msg = NO_CHATS_TEXTS.get(lang, NO_CHATS_TEXTS["en"])
        back_t = BACK_EMOJI_TEXTS.get(lang, BACK_EMOJI_TEXTS["en"])
        sent = await bot.send_message(
            chat_id, msg,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=back_t, callback_data="back_to_menu")]]),
        )
        await save_user_message(user_id, chat_id, sent.message_id)
        return
    keyboard_buttons = []
    for s in sessions:
        ad = await get_ad_by_id(int(s["ad_id"]))
        if not ad:
            continue
        content = ad.get("content") or ""
        ad_btn_preview = _ad_preview_short(content, 20)
        if int(s["user_a"]) == user_id:
            partner_name = (ad.get("author_name") or "Author")[:30]
        else:
            partner_name = (s.get("viewer_name") or "Someone")[:30]
        chat_btn = f"💬 {partner_name} · {ad_btn_preview}"
        keyboard_buttons.append([InlineKeyboardButton(text=chat_btn, callback_data=f"open_relay_{s['id']}")])
    back_t = BACK_EMOJI_TEXTS.get(lang, BACK_EMOJI_TEXTS["en"])
    keyboard_buttons.append([InlineKeyboardButton(text=back_t, callback_data="back_to_menu")])
    title = MY_CHATS_TEXTS.get(lang, MY_CHATS_TEXTS["en"])
    text = title
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


async def _admin_menu_keyboard() -> InlineKeyboardMarkup:
    pending = await get_pending_suspicious_count()
    pending_label = f"⚠️ Pending review ({pending})" if pending else "⚠️ Pending review"
    banned_count = await get_banned_users()
    banned_label = f"🚫 Banned users ({len(banned_count)})" if banned_count else "🚫 Banned users"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=pending_label, callback_data="admin_pending_review")],
            [InlineKeyboardButton(text="👥 Users", callback_data="admin_users")],
            [InlineKeyboardButton(text=banned_label, callback_data="admin_banned_users")],
            [InlineKeyboardButton(text="📋 Ads", callback_data="admin_ads")],
            [InlineKeyboardButton(text="🗑️ Clear database", callback_data="admin_clear")],
            [InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats")],
            [InlineKeyboardButton(text="🌐 Promo page", callback_data="admin_promo")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="admin_back_to_menu")],
        ]
    )


def _admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]]
    )


async def _draw_admin_menu(bot: Bot, user_id: int, chat_id: int):
    if ADMIN_USER_ID is None or user_id != ADMIN_USER_ID:
        await set_user_state_db(user_id, USER_STATE_MAIN_MENU)
        await _draw_main_menu(bot, user_id, chat_id)
        return
    kb = await _admin_menu_keyboard()
    sent = await bot.send_message(
        chat_id, "⚙️ Admin",
        reply_markup=kb,
    )
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
    elif new_state == USER_STATE_ADMIN_MENU:
        await _draw_admin_menu(bot, user_id, cid)
    elif new_state == USER_STATE_FEEDBACK:
        await _draw_feedback_prompt(bot, user_id, cid)
    else:
        await _draw_main_menu(bot, user_id, cid)


@router.message(CommandStart())
async def cmd_start(message: Message):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        bot = message.bot
        if await get_user_banned(user_id):
            lang = await get_user_language(user_id)
            text = BLOCKED_TEXTS.get(lang, BLOCKED_TEXTS["en"])
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="💬 Contact admin", callback_data="feedback")]]
            )
            sent = await bot.send_message(chat_id, text, reply_markup=kb)
            await save_user_message(user_id, chat_id, sent.message_id)
            return
        log.info("User %s started bot", user_id)
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
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        bot = callback.bot
        if not await _check_not_banned(bot, user_id, chat_id):
            return
        lang = callback.data.replace("lang_", "")
        if lang not in LANGUAGES:
            lang = "en"
        await set_user_language(user_id, lang)
        log.info("User %s chose language %s", user_id, lang)
        # Always show community rules after language selection (every /start)
        rules_text = RULES_TEXTS.get(lang, RULES_TEXTS["en"])
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=I_UNDERSTAND_TEXTS.get(lang, I_UNDERSTAND_TEXTS["en"]), callback_data="rules_accept")]]
        )
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=callback.message.message_id,
                text=rules_text,
                reply_markup=kb,
            )
        except Exception:
            sent = await bot.send_message(chat_id, rules_text, reply_markup=kb)
            try:
                await bot.delete_message(chat_id=chat_id, message_id=callback.message.message_id)
            except Exception:
                pass
            await save_user_message(user_id, chat_id, sent.message_id)
        else:
            await save_user_message(user_id, chat_id, callback.message.message_id)
        await set_user_state_db(user_id, USER_STATE_MAIN_MENU)
    except Exception:
        log.exception("on_language failed")


@router.callback_query(F.data == "rules_accept")
async def on_rules_accept(callback: CallbackQuery):
    try:
        await callback.answer()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        bot = callback.bot
        if not await _check_not_banned(bot, user_id, chat_id):
            return
        await set_state(bot, user_id, USER_STATE_MAIN_MENU, chat_id=chat_id)
    except Exception:
        log.exception("on_rules_accept failed")


@router.callback_query(F.data == "back_to_menu")
async def on_back_to_menu(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        if not await _check_not_banned(callback.bot, callback.from_user.id, callback.message.chat.id):
            return
        await state.clear()
        await set_state(callback.bot, callback.from_user.id, USER_STATE_MAIN_MENU, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_back_to_menu failed")


@router.callback_query(F.data == "ad_type_ok")
async def on_ad_type_ok(callback: CallbackQuery):
    """User confirmed detected ad type -> return to main menu."""
    try:
        await callback.answer()
        lang = await get_user_language(callback.from_user.id)
        await set_state(
            callback.bot, callback.from_user.id, USER_STATE_MAIN_MENU, chat_id=callback.message.chat.id,
            override_text=MAIN_MENU_TEXTS.get(lang, MAIN_MENU_TEXTS["en"]),
            override_kb=main_menu_keyboard(lang, callback.from_user.id),
        )
    except Exception:
        log.exception("on_ad_type_ok failed")


@router.callback_query(F.data.startswith("ad_type_change_"))
async def on_ad_type_change(callback: CallbackQuery):
    """Show 4 type options to change ad type."""
    try:
        await callback.answer()
        suffix = callback.data.replace("ad_type_change_", "").strip()
        try:
            ad_id = int(suffix)
        except ValueError:
            return
        lang = await get_user_language(callback.from_user.id)
        select_t = await translate_to("Select type:", LANGUAGES.get(lang, "Other"))
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=TYPE_LABEL_SELL.get(lang, TYPE_LABEL_SELL["en"]), callback_data=f"set_type_{ad_id}_SELL")],
                [InlineKeyboardButton(text=TYPE_LABEL_SEEK.get(lang, TYPE_LABEL_SEEK["en"]), callback_data=f"set_type_{ad_id}_SEEK")],
                [InlineKeyboardButton(text=TYPE_LABEL_GIVE.get(lang, TYPE_LABEL_GIVE["en"]), callback_data=f"set_type_{ad_id}_GIVE")],
                [InlineKeyboardButton(text=TYPE_LABEL_OTHER.get(lang, TYPE_LABEL_OTHER["en"]), callback_data=f"set_type_{ad_id}_OTHER")],
            ]
        )
        await callback.message.edit_text(select_t, reply_markup=kb)
    except Exception:
        log.exception("on_ad_type_change failed")


@router.callback_query(F.data == "ad_photo_skip")
async def on_ad_photo_skip(callback: CallbackQuery):
    """User skipped photo -> show ad confirmation (type correct/change)."""
    try:
        await callback.answer()
        user_id = callback.from_user.id
        ad_id = await get_user_pending_ad_id(user_id)
        if ad_id is None:
            await set_state(callback.bot, user_id, USER_STATE_MAIN_MENU, chat_id=callback.message.chat.id)
            return
        lang = await get_user_language(user_id)
        result_text, confirm_kb = await _build_ad_confirmation(ad_id, lang)
        await callback.message.edit_text(result_text, reply_markup=confirm_kb)
        await set_user_pending_ad_id(user_id, None)
        await set_user_state_db(user_id, USER_STATE_MAIN_MENU)
        await save_user_message(user_id, callback.message.chat.id, callback.message.message_id)
    except Exception:
        log.exception("on_ad_photo_skip failed")


@router.callback_query(F.data == "ad_photo_add")
async def on_ad_photo_add(callback: CallbackQuery):
    """User chose to add photo -> ask them to send it."""
    try:
        await callback.answer()
        user_id = callback.from_user.id
        if await get_user_state(user_id) != USER_STATE_POSTING_AD_PHOTO:
            return
        lang = await get_user_language(user_id)
        send_photo_t = SEND_PHOTO_NOW.get(lang, SEND_PHOTO_NOW["en"])
        await callback.message.edit_text(send_photo_t)
        await save_user_message(user_id, callback.message.chat.id, callback.message.message_id)
    except Exception:
        log.exception("on_ad_photo_add failed")


@router.callback_query(F.data.startswith("set_type_"))
async def on_set_type(callback: CallbackQuery):
    """User selected new ad type -> update DB and return to main menu."""
    try:
        await callback.answer()
        parts = callback.data.replace("set_type_", "").strip().split("_", 1)
        if len(parts) != 2:
            return
        try:
            ad_id = int(parts[0])
            ad_type = str(parts[1]).upper()
        except (ValueError, IndexError):
            return
        if ad_type not in ("SELL", "SEEK", "GIVE", "OTHER"):
            return
        await update_ad_type(ad_id, ad_type)
        await set_state(
            callback.bot, callback.from_user.id, USER_STATE_MAIN_MENU, chat_id=callback.message.chat.id,
        )
    except Exception:
        log.exception("on_set_type failed")


@router.callback_query(F.data == "post_ad")
async def on_post_ad(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        if not await _check_not_banned(callback.bot, callback.from_user.id, callback.message.chat.id):
            return
        await state.clear()
        await set_state(callback.bot, callback.from_user.id, USER_STATE_POSTING_AD, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_post_ad failed")


@router.callback_query(F.data == "view_ads")
async def on_view_ads(callback: CallbackQuery):
    try:
        await callback.answer()
        if not await _check_not_banned(callback.bot, callback.from_user.id, callback.message.chat.id):
            return
        await set_state(callback.bot, callback.from_user.id, USER_STATE_VIEWING_ADS, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_view_ads failed")


@router.callback_query(F.data == "feedback")
async def on_feedback(callback: CallbackQuery):
    try:
        await callback.answer()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        bot = callback.bot
        if await get_user_banned(user_id):
            lang = await get_user_language(user_id)
            prompt = FEEDBACK_PROMPT_TEXTS.get(lang, FEEDBACK_PROMPT_TEXTS["en"])
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text=BACK_TEXTS.get(lang, BACK_TEXTS["en"]), callback_data="back_to_menu")]]
            )
            try:
                await callback.message.edit_text(prompt, reply_markup=kb)
            except Exception:
                sent = await bot.send_message(chat_id, prompt, reply_markup=kb)
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await save_user_message(user_id, chat_id, sent.message_id)
                await set_user_state_db(user_id, USER_STATE_FEEDBACK)
                return
            await save_user_message(user_id, chat_id, callback.message.message_id)
            await set_user_state_db(user_id, USER_STATE_FEEDBACK)
        else:
            await set_state(bot, user_id, USER_STATE_FEEDBACK, chat_id=chat_id)
    except Exception:
        log.exception("on_feedback failed")


@router.callback_query(F.data == "view_ads_filter_open")
async def on_view_ads_filter_open(callback: CallbackQuery):
    """Show type filter options: ALL, SELL, SEEK, GIVE, OTHER."""
    try:
        await callback.answer()
        if not await _check_not_banned(callback.bot, callback.from_user.id, callback.message.chat.id):
            return
        lang = await get_user_language(callback.from_user.id)
        all_t = FILTER_ALL_TEXTS.get(lang, FILTER_ALL_TEXTS["en"])
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=all_t, callback_data="view_ads_filter_ALL")],
                [InlineKeyboardButton(text=TYPE_LABEL_SELL.get(lang, TYPE_LABEL_SELL["en"]), callback_data="view_ads_filter_SELL")],
                [InlineKeyboardButton(text=TYPE_LABEL_SEEK.get(lang, TYPE_LABEL_SEEK["en"]), callback_data="view_ads_filter_SEEK")],
                [InlineKeyboardButton(text=TYPE_LABEL_GIVE.get(lang, TYPE_LABEL_GIVE["en"]), callback_data="view_ads_filter_GIVE")],
                [InlineKeyboardButton(text=TYPE_LABEL_OTHER.get(lang, TYPE_LABEL_OTHER["en"]), callback_data="view_ads_filter_OTHER")],
            ]
        )
        filter_title = await translate_to("Filter by type:", LANGUAGES.get(lang, "Other"))
        await callback.message.edit_text(filter_title, reply_markup=kb)
    except Exception:
        log.exception("on_view_ads_filter_open failed")


@router.callback_query(F.data.startswith("view_ads_filter_"))
async def on_view_ads_filter_select(callback: CallbackQuery):
    """User selected a filter -> save and redraw View ads."""
    try:
        await callback.answer()
        if not await _check_not_banned(callback.bot, callback.from_user.id, callback.message.chat.id):
            return
        raw = callback.data or ""
        if not raw.startswith("view_ads_filter_"):
            return
        value = raw.replace("view_ads_filter_", "").strip()
        if value not in ("ALL", "SELL", "SEEK", "GIVE", "OTHER"):
            return
        await set_user_view_ads_filter(callback.from_user.id, value)
        await set_state(callback.bot, callback.from_user.id, USER_STATE_VIEWING_ADS, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_view_ads_filter_select failed")


def _require_admin(user_id: int) -> bool:
    return ADMIN_USER_ID is not None and user_id == ADMIN_USER_ID


async def _check_not_banned(bot: Bot, user_id: int, chat_id: int) -> bool:
    """If user is banned, send blocked message and return False. Otherwise return True."""
    if not await get_user_banned(user_id):
        return True
    lang = await get_user_language(user_id)
    text = BLOCKED_TEXTS.get(lang, BLOCKED_TEXTS["en"])
    try:
        await bot.send_message(chat_id, text)
    except Exception:
        pass
    return False


@router.callback_query(F.data == "admin_menu")
async def on_admin_menu(callback: CallbackQuery):
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        await set_state(callback.bot, callback.from_user.id, USER_STATE_ADMIN_MENU, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_admin_menu failed")


@router.callback_query(F.data == "admin_back_to_menu")
async def on_admin_back_to_menu(callback: CallbackQuery):
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        lang = await get_user_language(callback.from_user.id)
        await set_state(
            callback.bot, callback.from_user.id, USER_STATE_MAIN_MENU, chat_id=callback.message.chat.id,
            override_text=MAIN_MENU_TEXTS.get(lang, MAIN_MENU_TEXTS["en"]),
            override_kb=main_menu_keyboard(lang, callback.from_user.id),
        )
    except Exception:
        log.exception("on_admin_back_to_menu failed")


@router.callback_query(F.data == "admin_back")
async def on_admin_back(callback: CallbackQuery):
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        try:
            await callback.message.delete()
        except Exception:
            pass
        await set_state(
            callback.bot, callback.from_user.id, USER_STATE_ADMIN_MENU,
            chat_id=callback.message.chat.id
        )
    except Exception:
        log.exception("on_admin_back failed")


@router.callback_query(F.data == "admin_users")
async def on_admin_users(callback: CallbackQuery):
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        users = await get_all_users()
        lines = ["👥 Users\n"]
        buttons = []
        for u in users:
            uid = u.get("user_id") or "?"
            lang = u.get("language") or "?"
            created = u.get("created_at") or "—"
            if created and created != "—":
                try:
                    created = str(created)[:19]
                except Exception:
                    pass
            is_banned = u.get("is_banned") if isinstance(u.get("is_banned"), bool) else bool(u.get("is_banned"))
            lines.append(f"User {uid} · {lang} · {created}")
            ban_btn = InlineKeyboardButton(text=f"✅ Unban {uid}", callback_data=f"admin_unban_{uid}") if is_banned else InlineKeyboardButton(text=f"🚫 Ban {uid}", callback_data=f"admin_ban_{uid}")
            del_btn = InlineKeyboardButton(text=f"🗑️ Delete {uid}", callback_data=f"admin_delete_user_{uid}")
            buttons.append([ban_btn, del_btn])
        buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")])
        text = "\n".join(lines) if lines else "👥 No users."
        if len(text) > 4000:
            text = text[:3997] + "..."
        try:
            await callback.message.edit_text(
                text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            sent = await callback.bot.send_message(
                callback.message.chat.id,
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
            await save_user_message(
                callback.from_user.id, callback.message.chat.id, sent.message_id
            )
    except Exception:
        log.exception("on_admin_users failed")


@router.callback_query(F.data == "admin_banned_users")
async def on_admin_banned_users(callback: CallbackQuery):
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        users = await get_banned_users()
        lines = ["🚫 Banned users\n"]
        buttons = []
        for u in users:
            uid = u.get("user_id") or "?"
            lang = u.get("language") or "?"
            created = u.get("created_at") or "—"
            if created and created != "—":
                try:
                    created = str(created)[:19]
                except Exception:
                    pass
            lines.append(f"User {uid} · {lang} · {created}")
            buttons.append([InlineKeyboardButton(text=f"✅ Unban {uid}", callback_data=f"admin_unban_{uid}")])
        buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")])
        text = "\n".join(lines) if lines else "🚫 No banned users."
        if len(text) > 4000:
            text = text[:3997] + "..."
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        log.exception("on_admin_banned_users failed")


@router.callback_query(F.data.startswith("admin_ban_"))
async def on_admin_ban(callback: CallbackQuery):
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        try:
            target_id = int(callback.data.replace("admin_ban_", "").strip())
        except ValueError:
            return
        await set_user_banned(target_id, True)
        log.info("ADMIN: banned user %s", target_id)
        await set_state(callback.bot, callback.from_user.id, USER_STATE_ADMIN_MENU, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_admin_ban failed")


@router.callback_query(F.data.startswith("admin_unban_"))
async def on_admin_unban(callback: CallbackQuery):
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        try:
            target_id = int(callback.data.replace("admin_unban_", "").strip())
        except ValueError:
            return
        await set_user_banned(target_id, False)
        log.info("ADMIN: unbanned user %s", target_id)
        await set_state(callback.bot, callback.from_user.id, USER_STATE_ADMIN_MENU, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_admin_unban failed")


@router.callback_query(F.data == "admin_ads")
async def on_admin_ads(callback: CallbackQuery):
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        ads = await get_all_active_ads_admin()
        lines = ["📋 Active ads\n"]
        buttons = []
        for ad in ads:
            aid = ad.get("id")
            author = (ad.get("author_name") or "?")[:30]
            atype = ad.get("type") or "?"
            content_preview = _ad_preview_short(ad.get("content") or "", 60)
            expires = str(ad.get("expires_at") or "?")[:19]
            lines.append(f"#{aid} {author} · {atype}\n{content_preview}\nExpires: {expires}")
            buttons.append([InlineKeyboardButton(text=f"🗑️ Delete #{aid}", callback_data=f"admin_del_ad_{aid}")])
        buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")])
        text = "\n\n".join(lines) if lines else "📋 No active ads."
        if len(text) > 4000:
            text = text[:3997] + "..."
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        log.exception("on_admin_ads failed")


@router.callback_query(F.data.startswith("admin_delete_user_"))
async def on_admin_delete_user(callback: CallbackQuery):
    """Show delete-user confirmation or perform delete if confirm."""
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        raw = callback.data or ""
        if raw.startswith("admin_delete_user_confirm_"):
            try:
                target_id = int(raw.replace("admin_delete_user_confirm_", "").strip())
            except ValueError:
                return
            await admin_delete_user(target_id)
            log.info("ADMIN: deleted user %s", target_id)
            users = await get_all_users()
            lines = ["👥 Users\n"]
            buttons = []
            for u in users:
                uid = u.get("user_id") or "?"
                lang = u.get("language") or "?"
                created = u.get("created_at") or "—"
                if created and created != "—":
                    try:
                        created = str(created)[:19]
                    except Exception:
                        pass
                is_banned = u.get("is_banned") if isinstance(u.get("is_banned"), bool) else bool(u.get("is_banned"))
                lines.append(f"User {uid} · {lang} · {created}")
                ban_btn = InlineKeyboardButton(text=f"✅ Unban {uid}", callback_data=f"admin_unban_{uid}") if is_banned else InlineKeyboardButton(text=f"🚫 Ban {uid}", callback_data=f"admin_ban_{uid}")
                del_btn = InlineKeyboardButton(text=f"🗑️ Delete {uid}", callback_data=f"admin_delete_user_{uid}")
                buttons.append([ban_btn, del_btn])
            buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")])
            text = "\n".join(lines) if lines else "👥 No users."
            if len(text) > 4000:
                text = text[:3997] + "..."
            try:
                await callback.message.edit_text(
                    text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
                )
            except Exception:
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                sent = await callback.bot.send_message(
                    callback.message.chat.id,
                    text,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
                )
                await save_user_message(
                    callback.from_user.id, callback.message.chat.id, sent.message_id
                )
            return
        if raw.startswith("admin_delete_user_"):
            try:
                target_id = int(raw.replace("admin_delete_user_", "").strip())
            except ValueError:
                return
            await callback.message.edit_text(
                "Delete this user? Their ads and chats will also be deleted.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="✅ Confirm", callback_data=f"admin_delete_user_confirm_{target_id}")],
                        [InlineKeyboardButton(text="❌ Cancel", callback_data="admin_users")],
                    ]
                ),
            )
    except Exception:
        log.exception("on_admin_delete_user failed")


@router.callback_query(F.data.startswith("admin_del_ad_"))
async def on_admin_del_ad(callback: CallbackQuery):
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        try:
            ad_id = int(callback.data.replace("admin_del_ad_", "").strip())
        except ValueError:
            return
        await admin_delete_ad(ad_id)
        log.info("ADMIN: deleted ad %s", ad_id)
        await set_state(callback.bot, callback.from_user.id, USER_STATE_ADMIN_MENU, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_admin_del_ad failed")


@router.callback_query(F.data == "admin_clear")
async def on_admin_clear(callback: CallbackQuery):
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        await callback.message.edit_text(
            "🗑️ Clear database?\n\nThis will delete all ads and relay sessions. Users are kept. Confirm?",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Yes, clear all", callback_data="admin_clear_confirm")],
                    [InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")],
                ]
            ),
        )
    except Exception:
        log.exception("on_admin_clear failed")


@router.callback_query(F.data == "admin_clear_confirm")
async def on_admin_clear_confirm(callback: CallbackQuery):
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        await admin_clear_ads_and_relays()
        log.info("ADMIN: cleared database (ads and relay sessions)")
        await callback.message.edit_text("Done. All ads and relay sessions deleted.", reply_markup=_admin_back_keyboard())
    except Exception:
        log.exception("on_admin_clear_confirm failed")


@router.callback_query(F.data == "admin_stats")
async def on_admin_stats(callback: CallbackQuery):
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        total_users = len(await get_all_users())
        total_ads = await get_ads_count()
        active_relays = await count_active_relay_sessions()
        text = f"📊 Stats\n\nTotal users: {total_users}\nActive ads: {total_ads}\nActive relay sessions: {active_relays}"
        await callback.message.edit_text(text, reply_markup=_admin_back_keyboard())
    except Exception:
        log.exception("on_admin_stats failed")


@router.callback_query(F.data == "admin_promo")
async def on_admin_promo(callback: CallbackQuery):
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        await callback.bot.send_message(
            callback.message.chat.id,
            "Promo page for sharing with residents\n\nhttps://iamweasel89.github.io/vapenka24/",
        )
    except Exception:
        log.exception("on_admin_promo failed")


async def _redraw_pending_review(bot: Bot, chat_id: int, message_id: int) -> None:
    """Build and edit the pending suspicious ads screen. Used by admin_pending_review and after Remove/Keep."""
    pending = await get_pending_suspicious_ads()
    back_btn = [InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]
    if not pending:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="⚠️ Pending review\n\nNo pending reviews.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[back_btn]),
        )
        return
    lines = ["⚠️ Pending review\n"]
    buttons = []
    max_content = 350
    for item in pending:
        ad_id = item.get("ad_id")
        content = (item.get("content") or "").strip()
        content_show = content[:max_content] + "..." if len(content) > max_content else content
        ru = await translate_to(content_show if content_show else "(empty)", "Russian")
        ru_show = ru[:max_content] + "..." if len(ru) > max_content else ru
        lines.append(f"--- Ad #{ad_id} ---")
        lines.append("Original:\n" + content_show)
        lines.append("Russian:\n" + ru_show)
        lines.append("")
        buttons.append([
            InlineKeyboardButton(text="🗑️ Remove", callback_data=f"admin_suspicious_remove_{ad_id}"),
            InlineKeyboardButton(text="✅ Keep", callback_data=f"admin_suspicious_keep_{ad_id}"),
        ])
    buttons.append(back_btn)
    text = "\n".join(lines).strip()
    if len(text) > 4000:
        text = text[:3997] + "\n..."
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data == "admin_pending_review")
async def on_admin_pending_review(callback: CallbackQuery):
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        await _redraw_pending_review(
            callback.bot,
            callback.message.chat.id,
            callback.message.message_id,
        )
    except Exception:
        log.exception("on_admin_pending_review failed")


@router.callback_query(F.data.startswith("admin_suspicious_remove_"))
async def on_admin_suspicious_remove(callback: CallbackQuery):
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        try:
            ad_id = int(callback.data.replace("admin_suspicious_remove_", "").strip())
        except ValueError:
            return
        notif_chat_id, notif_msg_id = await get_suspicious_notification(ad_id)
        if notif_chat_id is not None and notif_msg_id is not None:
            try:
                await callback.bot.delete_message(chat_id=notif_chat_id, message_id=notif_msg_id)
            except Exception:
                pass
        await update_suspicious_status(ad_id, "removed")
        await admin_delete_ad(ad_id)
        log.info("ADMIN_MODERATION: ad %s removed by admin", ad_id)
        await _redraw_pending_review(
            callback.bot,
            callback.message.chat.id,
            callback.message.message_id,
        )
    except Exception:
        log.exception("on_admin_suspicious_remove failed")


@router.callback_query(F.data.startswith("admin_suspicious_keep_"))
async def on_admin_suspicious_keep(callback: CallbackQuery):
    try:
        await callback.answer()
        if not _require_admin(callback.from_user.id):
            return
        try:
            ad_id = int(callback.data.replace("admin_suspicious_keep_", "").strip())
        except ValueError:
            return
        notif_chat_id, notif_msg_id = await get_suspicious_notification(ad_id)
        if notif_chat_id is not None and notif_msg_id is not None:
            try:
                await callback.bot.delete_message(chat_id=notif_chat_id, message_id=notif_msg_id)
            except Exception:
                pass
        await update_suspicious_status(ad_id, "kept")
        log.info("ADMIN_MODERATION: ad %s kept by admin", ad_id)
        await _redraw_pending_review(
            callback.bot,
            callback.message.chat.id,
            callback.message.message_id,
        )
    except Exception:
        log.exception("on_admin_suspicious_keep failed")


@router.callback_query(F.data == "my_chats")
async def on_my_chats(callback: CallbackQuery):
    try:
        await callback.answer()
        if not await _check_not_banned(callback.bot, callback.from_user.id, callback.message.chat.id):
            return
        await set_state(callback.bot, callback.from_user.id, USER_STATE_MY_CHATS, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_my_chats failed")


@router.callback_query(F.data == "back_to_chats")
async def on_back_to_chats(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        if not await _check_not_banned(callback.bot, callback.from_user.id, callback.message.chat.id):
            return
        await state.clear()
        await set_user_current_relay_id(callback.from_user.id, None)
        await set_state(callback.bot, callback.from_user.id, USER_STATE_MY_CHATS, chat_id=callback.message.chat.id)
    except Exception:
        log.exception("on_back_to_chats failed")


@router.callback_query(F.data.startswith(CALLBACK_REPLY_AD_PREFIX))
async def on_reply_ad(callback: CallbackQuery):
    try:
        await callback.answer()
        if not await _check_not_banned(callback.bot, callback.from_user.id, callback.message.chat.id):
            return
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
        existing = await relay_find_active_session(viewer_id, author_id, ad_id)
        if existing:
            session_id = int(existing["id"])
            log.info("Reusing existing relay session_id=%s", session_id)
        else:
            session_id = await relay_create(viewer_id, author_id, ad_id, viewer_name=viewer_name)
            log.info("Relay session started: session_id=%s, user_a=%s, user_b=%s, ad_id=%s", session_id, viewer_id, author_id, ad_id)
        await set_user_current_relay_id(viewer_id, session_id)
        lang_viewer = await get_user_language(viewer_id)
        if existing:
            opening_text = await _build_relay_ui_text(session_id, viewer_id, lang_viewer)
            if len(opening_text) > 4000:
                opening_text = opening_text[:3997] + "..."
        else:
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
        await callback.answer()
        if not await _check_not_banned(callback.bot, callback.from_user.id, callback.message.chat.id):
            return
        await state.clear()
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
            menu_text = MAIN_MENU_TEXTS.get(lang, MAIN_MENU_TEXTS["en"])
            override = f"{chat_ended}\n\n{menu_text}"
            await set_state(bot, uid, USER_STATE_MAIN_MENU, override_text=override, override_kb=main_menu_keyboard(lang, uid))
    except Exception:
        log.exception("on_relay_stop failed")


def _format_user_text(raw: str) -> str:
    """Clean format for display: strip, normalize newlines, limit length."""
    if not raw:
        return ""
    text = "\n".join(line.strip() for line in (raw or "").strip().splitlines())
    return text[:4000] if len(text) > 4000 else text


async def _build_ad_confirmation(ad_id: int, lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """Build confirmation text and keyboard for a published ad (after Skip or Add photo)."""
    ad = await get_ad_by_id(ad_id)
    if not ad:
        confirm = await translate_to("Ad published.", LANGUAGES.get(lang, "Other"))
        return confirm, InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BACK_TEXTS.get(lang, "Back"), callback_data="ad_type_ok")]])
    formatted = _format_user_text(ad.get("content") or "")
    detected_type = ad.get("type") or "OTHER"
    type_label = _ad_type_label(detected_type, lang)
    confirm = await translate_to("Ad published.", LANGUAGES.get(lang, "Other"))
    result_text = f"✅ {confirm}\n\n🏷 {await translate_to('Detected type:', LANGUAGES.get(lang, 'Other'))} {type_label}\n\n{formatted}"
    correct_t = CONFIRM_TYPE_CORRECT.get(lang, CONFIRM_TYPE_CORRECT["en"])
    change_t = CONFIRM_TYPE_CHANGE.get(lang, CONFIRM_TYPE_CHANGE["en"])
    confirm_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=correct_t, callback_data="ad_type_ok")],
            [InlineKeyboardButton(text=change_t, callback_data=f"ad_type_change_{ad_id}")],
        ]
    )
    return result_text, confirm_kb


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

        if state == USER_STATE_FEEDBACK:
            raw = (message.text or "").strip()
            if not raw:
                lang = await get_user_language(user_id)
                prompt = FEEDBACK_PROMPT_TEXTS.get(lang, FEEDBACK_PROMPT_TEXTS["en"])
                await bot.send_message(chat_id, prompt)
                return
            sent_confirm = await bot.send_message(chat_id, "✅ Sent")
            lang = await get_user_language(user_id)
            lang_name = LANGUAGES.get(lang, LANGUAGES["en"])
            user_name = message.from_user.full_name or message.from_user.username or str(user_id)
            try:
                translation_ru = await translate_to(raw, "Russian")
            except Exception:
                translation_ru = raw
            admin_text = (
                f"💬 Feedback from {user_name} ({lang_name}):\n"
                f"Original: {raw}\n"
                f"Russian: {translation_ru}"
            )
            if ADMIN_USER_ID:
                admin_chat_id = await get_user_chat_id(ADMIN_USER_ID)
                if admin_chat_id:
                    try:
                        feedback_kb = InlineKeyboardMarkup(
                            inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]]
                        )
                        await bot.send_message(admin_chat_id, admin_text, reply_markup=feedback_kb)
                    except Exception as e:
                        log.warning("Failed to send feedback to admin: %s", e)
            await asyncio.sleep(1.5)
            try:
                await sent_confirm.delete()
            except Exception:
                pass
            await set_state(bot, user_id, USER_STATE_MAIN_MENU, chat_id=chat_id)
            return

        if not await _check_not_banned(bot, user_id, chat_id):
            return

        if state == USER_STATE_POSTING_AD_PHOTO:
            try:
                await message.delete()
            except Exception:
                pass
            lang = await get_user_language(user_id)
            send_photo_t = SEND_PHOTO_NOW.get(lang, SEND_PHOTO_NOW["en"])
            await bot.send_message(chat_id, send_photo_t)
            return

        if state == USER_STATE_POSTING_AD:
            processing = await translate_to("⏳ Publishing...", LANGUAGES.get(await get_user_language(user_id), "Other"))
            proc_msg = await bot.send_message(chat_id, processing)
            lang = await get_user_language(user_id)
            raw = (message.text or "").strip()
            verdict, reason = await moderate_content(raw)
            if verdict == "REJECTED":
                log.info("MODERATION: ad REJECTED - %s", reason or "")
                try:
                    await proc_msg.delete()
                except Exception:
                    pass
                polite = await translate_to("Your ad could not be published.", LANGUAGES.get(lang, "Other"))
                reason_t = await translate_to(reason or "Content not allowed", LANGUAGES.get(lang, "Other"))
                await set_state(
                    bot, user_id, USER_STATE_MAIN_MENU, chat_id=chat_id,
                    override_text=f"❌ {polite}\n\n{reason_t}", override_kb=main_menu_keyboard(lang, user_id),
                )
                return
            author_name = message.from_user.full_name or message.from_user.username or str(user_id)
            save_task = save_ad(user_id, lang, raw, author_name, ad_type="OTHER")
            classify_task = classify_ad_type(raw)
            ad_id, detected_type = await asyncio.gather(save_task, classify_task)
            log.info("MODERATION: ad %s APPROVED", ad_id)
            await update_ad_type(ad_id, detected_type)
            if verdict == "SUSPICIOUS":
                log.info("MODERATION: ad %s SUSPICIOUS - %s", ad_id, reason or "")
                await insert_suspicious_ad(ad_id)
                admin_chat_id = await get_user_chat_id(ADMIN_USER_ID) if ADMIN_USER_ID else None
                if admin_chat_id:
                    sent = await bot.send_message(
                        admin_chat_id,
                        "⚠️ New suspicious ad requires review",
                    )
                    await update_suspicious_notification(ad_id, admin_chat_id, sent.message_id)
            add_photo_prompt = ADD_PHOTO_PROMPT.get(lang, ADD_PHOTO_PROMPT["en"])
            add_photo_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=ADD_PHOTO_BTN.get(lang, ADD_PHOTO_BTN["en"]), callback_data="ad_photo_add")],
                    [InlineKeyboardButton(text=SKIP_PHOTO_BTN.get(lang, SKIP_PHOTO_BTN["en"]), callback_data="ad_photo_skip")],
                ]
            )
            prompt_chat_id, prompt_msg_id = await get_user_message_ids(user_id)
            if prompt_chat_id and prompt_msg_id and prompt_msg_id != proc_msg.message_id:
                try:
                    await bot.delete_message(chat_id=prompt_chat_id, message_id=prompt_msg_id)
                except Exception:
                    pass
            try:
                await proc_msg.edit_text(add_photo_prompt, reply_markup=add_photo_kb)
            except Exception:
                sent = await bot.send_message(chat_id, add_photo_prompt, reply_markup=add_photo_kb)
                try:
                    await proc_msg.delete()
                except Exception:
                    pass
                await save_user_message(user_id, chat_id, sent.message_id)
            else:
                await save_user_message(user_id, chat_id, proc_msg.message_id)
            await set_user_state_db(user_id, USER_STATE_POSTING_AD_PHOTO)
            await set_user_pending_ad_id(user_id, ad_id)
            return
        if state == USER_STATE_IN_RELAY:
            relay_id = await get_user_current_relay_id(user_id)
            session = await relay_get_session_by_id(relay_id) if relay_id else None
            if not session:
                await set_state(bot, user_id, USER_STATE_MAIN_MENU, chat_id=chat_id)
                return
            proc_msg = await bot.send_message(chat_id, "⏳")
            await asyncio.sleep(1)
            try:
                await proc_msg.delete()
            except Exception:
                pass
            from_name = message.from_user.first_name or message.from_user.username or str(user_id)
            original = message.text or ""
            verdict, reason = await moderate_content(original)
            if verdict == "REJECTED":
                log.info("MODERATION: message REJECTED - %s", reason or "")
                my_lang = await get_user_language(user_id)
                prefix = await translate_to("Message not sent:", LANGUAGES.get(my_lang, "Other"))
                reason_t = await translate_to(reason or "Content not allowed", LANGUAGES.get(my_lang, "Other"))
                await bot.send_message(chat_id, f"❌ {prefix} {reason_t}")
                return
            log.info("MODERATION: message APPROVED (relay_id=%s)", session["id"])
            await relay_add_message(session["id"], user_id, from_name, original)
            other_id = await relay_get_other_user(session, user_id)
            other_lang = await get_user_language(other_id)
            other_lang_name = LANGUAGES.get(other_lang, LANGUAGES["en"])
            log.info("Relay message forwarded: from=%s to=%s", user_id, other_id)
            my_lang = await get_user_language(user_id)
            text_for_me = await _build_relay_ui_text(session["id"], user_id, my_lang)
            if len(text_for_me) > 4000:
                text_for_me = text_for_me[:3997] + "..."
            kb_me = relay_keyboard(my_lang, session["id"])
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
                        ad_preview = await translate_to(ad_preview, LANGUAGES.get(await get_user_language(other_id), LANGUAGES["en"]))
                    lang_other = await get_user_language(other_id)
                    label = NEW_MESSAGE_FROM_TEXTS.get(lang_other, NEW_MESSAGE_FROM_TEXTS["en"])
                    open_btn = OPEN_CHAT_BTN_TEXTS.get(lang_other, OPEN_CHAT_BTN_TEXTS["en"])
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
            warn_t = await translate_to("Please use the buttons below.", LANGUAGES.get(await get_user_language(user_id), "Other"))
            warn_msg = await bot.send_message(chat_id, f"⚠️ {warn_t}")
            await asyncio.sleep(2)
            try:
                await warn_msg.delete()
            except Exception:
                pass
    except Exception:
        log.exception("on_text_message failed")


@router.message(F.photo)
async def on_photo_message(message: Message):
    """Handle photo when user is in POSTING_AD_PHOTO (optional ad photo)."""
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        bot = message.bot
        state = await get_user_state(user_id)
        if state != USER_STATE_POSTING_AD_PHOTO:
            return
        ad_id = await get_user_pending_ad_id(user_id)
        if ad_id is None:
            return
        try:
            await message.delete()
        except Exception:
            pass
        photo = message.photo
        file_id = photo[-1].file_id if photo else None
        if not file_id:
            return
        await update_ad_photo(ad_id, file_id)
        lang = await get_user_language(user_id)
        result_text, confirm_kb = await _build_ad_confirmation(ad_id, lang)
        await set_user_pending_ad_id(user_id, None)
        await set_user_state_db(user_id, USER_STATE_MAIN_MENU)
        prompt_chat_id, prompt_msg_id = await get_user_message_ids(user_id)
        if prompt_chat_id and prompt_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=prompt_chat_id,
                    message_id=prompt_msg_id,
                    text=result_text,
                    reply_markup=confirm_kb,
                )
                await save_user_message(user_id, prompt_chat_id, prompt_msg_id)
            except Exception:
                sent = await bot.send_message(chat_id, result_text, reply_markup=confirm_kb)
                await save_user_message(user_id, chat_id, sent.message_id)
        else:
            sent = await bot.send_message(chat_id, result_text, reply_markup=confirm_kb)
            await save_user_message(user_id, chat_id, sent.message_id)
    except Exception:
        log.exception("on_photo_message failed")
