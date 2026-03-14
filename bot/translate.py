from openai import AsyncOpenAI

from bot.config import OPENAI_API_KEY


async def translate_to(text: str, language: str) -> str:
    if not OPENAI_API_KEY or not text.strip():
        return text
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
