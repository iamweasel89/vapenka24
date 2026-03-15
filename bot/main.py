import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN, DB_PATH
from bot.logging_config import setup_logging

setup_logging()

from bot.handlers.start import router as start_router


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'other',
                chat_id INTEGER,
                message_id INTEGER,
                state TEXT NOT NULL DEFAULT 'MAIN_MENU'
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                content TEXT NOT NULL,
                author_name TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'OTHER',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP DEFAULT (datetime('now', '+7 days')),
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
        try:
            await db.execute("ALTER TABLE ads ADD COLUMN expires_at TIMESTAMP")
            await db.commit()
            await db.execute(
                "UPDATE ads SET expires_at = datetime(created_at, '+7 days') WHERE expires_at IS NULL"
            )
            await db.commit()
        except aiosqlite.OperationalError:
            pass
        await db.execute(
            """CREATE TABLE IF NOT EXISTS relay_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_a INTEGER NOT NULL,
                user_b INTEGER NOT NULL,
                ad_id INTEGER NOT NULL,
                viewer_name TEXT,
                author_joined INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ad_id) REFERENCES ads(id)
            )"""
        )
        try:
            await db.execute("ALTER TABLE relay_sessions ADD COLUMN viewer_name TEXT")
            await db.commit()
        except aiosqlite.OperationalError:
            pass
        try:
            await db.execute("ALTER TABLE relay_sessions ADD COLUMN author_joined INTEGER NOT NULL DEFAULT 0")
            await db.commit()
        except aiosqlite.OperationalError:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN state TEXT NOT NULL DEFAULT 'MAIN_MENU'")
            await db.commit()
        except aiosqlite.OperationalError:
            pass
        try:
            await db.execute("ALTER TABLE relay_sessions ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
            await db.commit()
            await db.execute("UPDATE relay_sessions SET status = 'active' WHERE status IS NULL OR status = ''")
            await db.commit()
        except aiosqlite.OperationalError:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN current_relay_id INTEGER")
            await db.commit()
        except aiosqlite.OperationalError:
            pass
        try:
            await db.execute("ALTER TABLE ads ADD COLUMN type TEXT NOT NULL DEFAULT 'OTHER'")
            await db.commit()
        except aiosqlite.OperationalError:
            pass
        try:
            await db.execute("ALTER TABLE ads ADD COLUMN photo_id TEXT")
            await db.commit()
        except aiosqlite.OperationalError:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN pending_ad_id INTEGER")
            await db.commit()
        except aiosqlite.OperationalError:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN welcome_shown INTEGER DEFAULT 0")
            await db.commit()
        except aiosqlite.OperationalError:
            pass
        try:
            await db.execute("UPDATE ads SET type = 'SEEK' WHERE type = 'BUY'")
            await db.commit()
        except aiosqlite.OperationalError:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN view_ads_filter TEXT DEFAULT 'ALL'")
            await db.commit()
        except aiosqlite.OperationalError:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            await db.commit()
        except aiosqlite.OperationalError:
            pass
        await db.execute(
            """CREATE TABLE IF NOT EXISTS relay_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                relay_id INTEGER NOT NULL,
                from_user_id INTEGER NOT NULL,
                from_name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (relay_id) REFERENCES relay_sessions(id)
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS view_ads_messages (
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, message_id)
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS suspicious_ads (
                ad_id INTEGER PRIMARY KEY,
                notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'pending',
                FOREIGN KEY (ad_id) REFERENCES ads(id)
            )"""
        )
        for col, typ in [
            ("notification_chat_id", "INTEGER"),
            ("notification_message_id", "INTEGER"),
        ]:
            try:
                await db.execute(f"ALTER TABLE suspicious_ads ADD COLUMN {col} {typ}")
                await db.commit()
            except aiosqlite.OperationalError:
                pass
        await db.commit()


async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
