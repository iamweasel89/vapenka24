#!/usr/bin/env python3
"""
Standalone script to insert seed users and ads into the database.
Uses DATABASE_URL from environment (.env). Runs once and exits.
Prints confirmation for each inserted user and ad.
"""
import asyncio
import os
from datetime import datetime, timedelta

import asyncpg
from dotenv import load_dotenv

load_dotenv()

# (user_id, name, language)
SEED_USERS = [
    (10001, "Milan", "sk"),
    (10002, "Dmytro", "uk"),
    (10003, "Maria", "ro"),
    (10004, "Tomáš", "sk"),
]

# (user_id, author_name, type, content, date_str YYYY-MM-DD)
SEED_ADS = [
    (10002, "Dmytro", "SEEK", "Ищу соседа по комнате на долгий срок. Некурящий, тихий. Комната А116.", "2026-03-10"),
    (10001, "Milan", "SELL", "Продам наушники Sony проводные, рабочие. 20 евро.", "2026-03-10"),
    (10004, "Tomáš", "SELL", "Продам монитор 24 дюйма, HDMI. 60 евро.", "2026-03-11"),
    (10003, "Maria", "SELL", "Продам зимние ботинки, размер 38. Носила один сезон. 25 евро.", "2026-03-11"),
    (10001, "Milan", "SELL", "Продам велосипед, горный, б/у, хорошее состояние. 80 евро.", "2026-03-12"),
    (10004, "Tomáš", "GIVE", "Отдам кастрюли и сковородку. Переезжаю.", "2026-03-12"),
    (10002, "Dmytro", "SELL", "Продам электрочайник, почти новый. 12 евро.", "2026-03-13"),
    (10003, "Maria", "SELL", "Продам настольную лампу, рабочую. 8 евро.", "2026-03-13"),
    (10004, "Tomáš", "SEEK", "Ищу помощника с переездом на выходных. Заплачу.", "2026-03-13"),
    (10004, "Tomáš", "SELL", "Продам электросамокат, б/у, заряжается. 150 евро.", "2026-03-14"),
    (10001, "Milan", "GIVE", "Отдам мужскую куртку размер M. Не нужна.", "2026-03-14"),
    (10002, "Dmytro", "GIVE", "Отдам учебники по математике, университетские.", "2026-03-15"),
    (10003, "Maria", "GIVE", "Отдам косметику, неиспользованную.", "2026-03-15"),
]


def parse_date(date_str: str) -> datetime:
    """Parse YYYY-MM-DD as UTC midnight."""
    return datetime.strptime(date_str, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)


async def main() -> None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print("ERROR: DATABASE_URL is not set. Set it in .env or environment.")
        return

    conn = await asyncpg.connect(database_url)

    try:
        # Insert users (ON CONFLICT DO NOTHING)
        for user_id, name, language in SEED_USERS:
            await conn.execute(
                """INSERT INTO users (user_id, language, state)
                   VALUES ($1, $2, 'MAIN_MENU')
                   ON CONFLICT (user_id) DO NOTHING""",
                user_id,
                language,
            )
            print(f"User: user_id={user_id}, name={name}, language={language}")

        # Insert ads with explicit created_at and expires_at (created_at + 7 days)
        for user_id, author_name, ad_type, content, date_str in SEED_ADS:
            created_at = parse_date(date_str)
            expires_at = created_at + timedelta(days=7)
            await conn.execute(
                """INSERT INTO ads (user_id, language, content, author_name, type, created_at, expires_at, is_seed)
                   SELECT $1, u.language, $2, $3, $4, $5, $6, true
                   FROM users u WHERE u.user_id = $1""",
                user_id,
                content,
                author_name,
                ad_type,
                created_at,
                expires_at,
            )
            preview = content[:50] + "..." if len(content) > 50 else content
            print(f"Ad: {user_id} · {ad_type} · {date_str} · {preview}")

        print(f"Done. {len(SEED_USERS)} user(s), {len(SEED_ADS)} ad(s).")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
