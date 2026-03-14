import aiosqlite
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.config import DB_PATH, LANGUAGES
from bot.translate import translate_to


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

CHOOSE_LANG_TEXT = "Choose language / Vyberte jazyk / Tilni tanlang / Pumili ng wika / Оберіть мову:"


def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"lang_{code}")]
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


async def get_last_ads(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, user_id, language, content, author_name, created_at FROM ads ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
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
        except Exception:
            pass
    sent = await message.answer(CHOOSE_LANG_TEXT, reply_markup=lang_keyboard())
    await save_user_message(user_id, chat_id, sent.message_id)


@router.callback_query(F.data.startswith("lang_"))
async def on_language(callback: CallbackQuery):
    lang = callback.data.replace("lang_", "")
    if lang not in LANGUAGES:
        lang = "other"
    await set_user_language(callback.from_user.id, lang)
    text = MAIN_MENU_TEXTS.get(lang, MAIN_MENU_TEXTS["other"])
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard(lang))
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def on_back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    lang = await get_user_language(callback.from_user.id)
    text = MAIN_MENU_TEXTS.get(lang, MAIN_MENU_TEXTS["other"])
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard(lang))


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
    user_id = message.from_user.id
    bot = message.bot
    data = await state.get_data()
    lang = data.get("lang", "other")
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


@router.callback_query(F.data == "view_ads")
async def on_view_ads(callback: CallbackQuery):
    await callback.answer()
    lang = await get_user_language(callback.from_user.id)
    ads = await get_last_ads(10)
    if not ads:
        msg = NO_ADS.get(lang, NO_ADS["other"])
        await callback.message.edit_text(msg, reply_markup=back_keyboard(lang))
        return
    target_language = LANGUAGES.get(lang, "Other")
    lines = []
    for a in ads:
        ts = a["created_at"] or ""
        name = a["author_name"] or "Unknown"
        content = a["content"]
        if a.get("language") != lang:
            content = await translate_to(content, target_language)
        lines.append(f"👤 {name}\n🕐 {ts}\n{content}\n")
    text = "\n———\n".join(lines)
    if len(text) > 4000:
        text = text[:3997] + "..."
    await callback.message.edit_text(text, reply_markup=back_keyboard(lang))
