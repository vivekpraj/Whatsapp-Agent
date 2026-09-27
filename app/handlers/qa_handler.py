import requests
from app.config import GROQ_API_KEY

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are a concise personal assistant on WhatsApp. "
    "Reply in 1-3 sentences max. "
    "No markdown formatting. "
    "No bullet points. "
    "Plain text only."
)


def handle_qa(text: str) -> str:
    """
    Send the user's message to Groq LLaMA and return the answer.
    """
    try:
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "max_tokens": 300,
                "temperature": 0.7,
            },
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except requests.RequestException as e:
        return "Sorry, I could not reach the AI right now. Please try again."
    except (KeyError, IndexError):
        return "Sorry, I received an unexpected response. Please try again."
