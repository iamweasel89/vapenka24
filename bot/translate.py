from openai import AsyncOpenAI

from bot.config import OPENAI_API_KEY

MODERATION_PROMPT = """You classify ads for a residential dormitory bulletin board. Use exactly one of three verdicts.

REJECTED — Use ONLY for these four categories. Nothing else. If in doubt, do NOT use REJECTED.
1. Explicit threats or violence (direct threats to harm someone).
2. Illegal drugs (offering, selling, or seeking illegal drugs).
3. Adult/sexual services (prostitution, escort services, explicit sexual offers).
4. Hate speech (targeting people by race, religion, ethnicity, etc.).
Do NOT reject: cash payments, urgent requests, "no documents", "no box", used items, roommates, tutoring, everyday buying/selling, vague wording, or anything that is merely odd or unclear. Reserve REJECTED for clearly illegal or harmful content.

SUSPICIOUS — Publish the ad but flag for admin review. Use for: deliberately vague "services" or "stuff"; unusual urgency or payment conditions; possible stolen goods; ambiguous business/commercial offers; anything that seems odd but is NOT clearly illegal. Do NOT use SUSPICIOUS for normal listings (e.g. selling a bike, looking for a chair, cash only, urgent, no receipt).

APPROVED — Everything else. This includes: selling/buying used items (with or without box/documents), looking for roommates, cash payments, urgent requests, everyday commerce between neighbors, giving things away, tutoring, local services, and any normal personal ad. When unsure between APPROVED and SUSPICIOUS, prefer APPROVED. When unsure between APPROVED and REJECTED, always use APPROVED.

Reply with exactly one line: APPROVED or REJECTED: [brief reason] or SUSPICIOUS: [brief reason]"""


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
