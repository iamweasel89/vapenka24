import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

DB_PATH = os.getenv("DB_PATH", "vapenka24.db")

LANGUAGES = {
    "sk": "Slovak",
    "uz": "Uzbek",
    "tl": "Tagalog",
    "uk": "Ukrainian",
    "other": "Other",
}
