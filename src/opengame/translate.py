from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _cfg(key: str, default: str) -> str:
    return os.getenv(key, default).strip()


def translate_clipboard() -> str:
    """Read clipboard text and translate it via OpenAI. Returns the translated string."""
    try:
        import pyperclip

        text = pyperclip.paste()
    except Exception as exc:
        return f"[Clipboard error: {exc}]"

    if not text or not text.strip():
        return "[Clipboard is empty]"

    return _call_openai(text.strip())


def _call_openai(text: str) -> str:
    api_key = _cfg("OPENAI_API_KEY", "")
    base_url = _cfg("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = _cfg("TRANSLATE_MODEL", "gpt-4o-mini")
    target_lang = _cfg("TRANSLATE_LANG", "English")

    if not api_key:
        return "[OPENAI_API_KEY not set in .env]"

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Translate the text the user sends into {target_lang}. "
                        "Reply with the translation only — no explanations, no quotes."
                    ),
                },
                {"role": "user", "content": text},
            ],
            max_tokens=512,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        return f"[Translation error: {exc}]"
