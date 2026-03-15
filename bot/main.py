import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN, DATABASE_URL
from bot.db import init_pool, get_pool, close_pool
from bot.logging_config import setup_logging

setup_logging()

from bot.handlers.start import router as start_router


async def init_db():
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'en',
                chat_id BIGINT,
                message_id BIGINT,
                state TEXT NOT NULL DEFAULT 'MAIN_MENU',
                current_relay_id BIGINT,
                view_ads_filter TEXT DEFAULT 'ALL',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                pending_ad_id BIGINT,
                welcome_shown INTEGER DEFAULT 0,
                is_banned BOOLEAN NOT NULL DEFAULT false,
                rules_accepted INTEGER NOT NULL DEFAULT 0
            )"""
        )
        for sql in (
            "ALTER TABLE users ADD COLUMN is_banned BOOLEAN NOT NULL DEFAULT false",
            "ALTER TABLE users ADD COLUMN rules_accepted INTEGER NOT NULL DEFAULT 0",
        ):
            try:
                await conn.execute(sql)
            except Exception as e:
                if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                    raise
        try:
            await conn.execute("UPDATE users SET rules_accepted = 1 WHERE welcome_shown = 1")
        except Exception:
            pass
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS ads (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id),
                language TEXT NOT NULL,
                content TEXT NOT NULL,
                author_name TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'OTHER',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '7 days'),
                photo_id TEXT
            )"""
        )
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS relay_sessions (
                id SERIAL PRIMARY KEY,
                user_a BIGINT NOT NULL,
                user_b BIGINT NOT NULL,
                ad_id INTEGER NOT NULL REFERENCES ads(id),
                viewer_name TEXT,
                author_joined INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'active'
            )"""
        )
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS relay_messages (
                id SERIAL PRIMARY KEY,
                relay_id INTEGER NOT NULL REFERENCES relay_sessions(id),
                from_user_id BIGINT NOT NULL,
                from_name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS view_ads_messages (
                user_id BIGINT NOT NULL,
                chat_id BIGINT NOT NULL,
                message_id BIGINT NOT NULL,
                PRIMARY KEY (user_id, message_id)
            )"""
        )
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS suspicious_ads (
                ad_id INTEGER PRIMARY KEY REFERENCES ads(id),
                notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'pending',
                notification_chat_id BIGINT,
                notification_message_id BIGINT
            )"""
        )


async def main():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is required")
    await init_pool(DATABASE_URL)
    try:
        await init_db()
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(start_router)
        await dp.start_polling(bot)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
