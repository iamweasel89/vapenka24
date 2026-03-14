import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN, DB_PATH
from bot.handlers.start import router as start_router


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'other',
                chat_id INTEGER,
                message_id INTEGER
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                content TEXT NOT NULL,
                author_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )"""
        )
        await db.commit()
        for col, typ in [("chat_id", "INTEGER"), ("message_id", "INTEGER")]:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
                await db.commit()
            except aiosqlite.OperationalError:
                pass
        for col, typ in [("language", "TEXT"), ("author_name", "TEXT")]:
            try:
                await db.execute(f"ALTER TABLE ads ADD COLUMN {col} {typ}")
                await db.commit()
            except aiosqlite.OperationalError:
                pass


async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
