import requests
from app.llm import chat

SYSTEM_PROMPT = (
    "You are a concise personal assistant on WhatsApp. "
    "Reply in 1-3 sentences max. "
    "No markdown formatting. "
    "No bullet points. "
    "Plain text only."
)


def handle_qa(text: str) -> str:
    try:
        return chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            max_tokens=300,
            temperature=0.7,
        )
    except requests.RequestException:
        return "Sorry, I could not reach the AI right now. Please try again."
    except (KeyError, IndexError):
        return "Sorry, I received an unexpected response. Please try again."
