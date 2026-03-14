import aiosqlite
from aiogram import Router, F
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
            "INSERT INTO users (user_id, language) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET language = ?",
            (user_id, lang, lang),
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
    await message.answer(CHOOSE_LANG_TEXT, reply_markup=lang_keyboard())


@router.callback_query(F.data.startswith("lang_"))
async def on_language(callback: CallbackQuery):
    lang = callback.data.replace("lang_", "")
    if lang not in LANGUAGES:
        lang = "other"
    await set_user_language(callback.from_user.id, lang)
    text = MAIN_MENU_TEXTS.get(lang, MAIN_MENU_TEXTS["other"])
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard(lang))
    await callback.answer()


@router.callback_query(F.data == "post_ad")
async def on_post_ad(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = await get_user_language(callback.from_user.id)
    await state.set_state(PostAdStates.waiting_text)
    await state.update_data(lang=lang)
    prompt = ENTER_AD_TEXT.get(lang, ENTER_AD_TEXT["other"])
    await callback.message.answer(prompt)


@router.message(PostAdStates.waiting_text, F.text)
async def on_ad_text(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "other")
    author_name = message.from_user.full_name or message.from_user.username or str(message.from_user.id)
    await save_ad(message.from_user.id, lang, message.text, author_name)
    await state.clear()
    confirm = AD_POSTED.get(lang, AD_POSTED["other"])
    await message.answer(confirm)


@router.callback_query(F.data == "view_ads")
async def on_view_ads(callback: CallbackQuery):
    await callback.answer()
    lang = await get_user_language(callback.from_user.id)
    ads = await get_last_ads(10)
    if not ads:
        msg = NO_ADS.get(lang, NO_ADS["other"])
        await callback.message.answer(msg)
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
    await callback.message.answer(text)
