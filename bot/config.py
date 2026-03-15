import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")


def _admin_user_id() -> int | None:
    raw = os.getenv("ADMIN_USER_ID", "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


ADMIN_USER_ID = _admin_user_id()

LANGUAGES = {
    "sk": "Slovak",
    "uz": "Uzbek",
    "tl": "Tagalog",
    "uk": "Ukrainian",
    "ro": "Romanian",
    "en": "English",
    "hu": "Hungarian",
    "other": "Other",
}
