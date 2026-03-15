from openai import AsyncOpenAI

from bot.config import OPENAI_API_KEY

MODERATION_PROMPT = """Is this text appropriate for a residential dormitory bulletin board?
APPROVED: All normal peer-to-peer trading — buying/selling everyday items (bikes, furniture, food, clothes, books, electronics, etc.), giving away items, seeking roommates, tutoring, local services. Default to APPROVED for any clear personal ad or straightforward commerce between residents.
REJECT only if it contains: explicit threats or violence, illegal drugs, adult/sexual services, hate speech.
SUSPICIOUS: Only when there are genuine red flags — e.g. deliberately vague "services" or "stuff", unusual requests that suggest code words, or commercial/business offers disguised as personal ads. Do NOT flag normal listings (e.g. "selling my bike", "looking for a chair", "free coffee") as SUSPICIOUS.
Reply with only: APPROVED or REJECTED: [brief reason] or SUSPICIOUS: [brief reason]"""


async def moderate_content(text: str) -> tuple[str, str | None]:
    """
    Check content with OpenAI. Returns (verdict, reason) where verdict is APPROVED, REJECTED, or SUSPICIOUS.
    reason is set for REJECTED and SUSPICIOUS. On API error, returns (APPROVED, None).
    """
    if not OPENAI_API_KEY or not (text or "").strip():
        return "APPROVED", None
    try:
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"{MODERATION_PROMPT}\n\n{text.strip()}"}],
        )
        if not resp.choices or not resp.choices[0].message.content:
            return "APPROVED", None
        content = resp.choices[0].message.content.strip()
        raw = content.upper()
        if raw.startswith("REJECTED"):
            reason = content
            if ":" in reason:
                reason = reason.split(":", 1)[1].strip()
            else:
                reason = reason.replace("REJECTED", "").strip() or "Content not allowed"
            return "REJECTED", reason[:500]
        if raw.startswith("SUSPICIOUS"):
            reason = content
            if ":" in reason:
                reason = reason.split(":", 1)[1].strip()
            else:
                reason = reason.replace("SUSPICIOUS", "").strip() or "Unusual content"
            return "SUSPICIOUS", reason[:500]
        return "APPROVED", None
    except Exception:
        return "APPROVED", None


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
