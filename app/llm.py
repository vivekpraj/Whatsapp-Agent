import time
import requests
from app.config import GEMINI_API_KEY

GEMINI_MODEL = "gemini-2.0-flash"


def chat(messages: list[dict], max_tokens: int = 300, temperature: float = 0.7) -> str:
    """
    Send a chat request to Gemini native REST API.
    Converts OpenAI-style messages to Gemini format.
    Retries once on 429 (rate limit).
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    # Convert OpenAI messages to Gemini format
    system_text = ""
    gemini_contents = []
    for msg in messages:
        if msg["role"] == "system":
            system_text = msg["content"]
        elif msg["role"] == "user":
            gemini_contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
        elif msg["role"] == "assistant":
            gemini_contents.append({"role": "model", "parts": [{"text": msg["content"]}]})

    payload = {
        "contents": gemini_contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }
    if system_text:
        payload["systemInstruction"] = {"parts": [{"text": system_text}]}

    for attempt in range(2):
        resp = requests.post(url, json=payload, timeout=20)
        if resp.status_code == 429 and attempt == 0:
            time.sleep(5)
            continue
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    resp.raise_for_status()
    return ""
