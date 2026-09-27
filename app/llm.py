import time
import requests
from app.config import GEMINI_API_KEY

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"


def chat(messages: list[dict], max_tokens: int = 300, temperature: float = 0.7) -> str:
    """
    Send a chat request to NVIDIA NIM (OpenAI-compatible).
    Retries once on 429 (rate limit).
    """
    payload = {
        "model": NVIDIA_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }

    for attempt in range(2):
        resp = requests.post(NVIDIA_URL, headers=headers, json=payload, timeout=20)
        if resp.status_code == 429 and attempt == 0:
            time.sleep(5)
            continue
        if not resp.ok:
            import logging
            logging.getLogger(__name__).error("NVIDIA NIM error %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    resp.raise_for_status()
    return ""
