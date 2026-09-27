import time
import requests
from app.config import GEMINI_API_KEY

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GEMINI_MODEL = "gemini-2.0-flash"

_HEADERS = {
    "Content-Type": "application/json",
}


def chat(messages: list[dict], max_tokens: int = 300, temperature: float = 0.7) -> str:
    """
    Send a chat request to Gemini via its OpenAI-compatible endpoint.
    Retries once on 429 (rate limit) after a short wait.
    Raises on other HTTP errors.
    """
    payload = {
        "model": GEMINI_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    headers = {**_HEADERS, "Authorization": f"Bearer {GEMINI_API_KEY}"}

    for attempt in range(2):
        resp = requests.post(GEMINI_URL, headers=headers, json=payload, timeout=20)
        if resp.status_code == 429 and attempt == 0:
            time.sleep(5)
            continue
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    resp.raise_for_status()
    return ""
