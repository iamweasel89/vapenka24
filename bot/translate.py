from openai import AsyncOpenAI

from bot.config import OPENAI_API_KEY

AD_TYPES = ("SELL", "SEEK", "GIVE", "OTHER")

CLASSIFY_PROMPT = """Classify this ad into one of: SELL, SEEK, GIVE, OTHER.
SELL: selling items.
SEEK: looking for something or someone (roommate, item, service, help).
GIVE: giving away for free.
OTHER: everything else.
Reply with just the category word, nothing else."""


async def classify_ad_type(ad_text: str) -> str:
    """Classify ad into SELL, SEEK, GIVE, or OTHER. Returns OTHER on error or empty."""
    if not OPENAI_API_KEY or not (ad_text or "").strip():
        return "OTHER"
    try:
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"{CLASSIFY_PROMPT}\n\n{ad_text.strip()}"}],
        )
        if resp.choices and resp.choices[0].message.content:
            raw = resp.choices[0].message.content.strip().upper()
            if raw == "BUY":
                raw = "SEEK"
            for t in AD_TYPES:
                if t in raw or raw == t:
                    return t
    except Exception:
        pass
    return "OTHER"


async def translate_to(text: str, language: str) -> str:
    if not OPENAI_API_KEY or not text.strip():
        return text
    print(f"DEBUG: translate_to called, target language={language!r}, text_len={len(text)}")
    prompt = f"Translate the following text to {language}. Return only the translated text, nothing else: {text}"
    try:
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        if resp.choices and resp.choices[0].message.content:
            return resp.choices[0].message.content.strip()
    except Exception:
        pass
    return text
