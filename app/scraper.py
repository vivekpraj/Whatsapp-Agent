import requests

JINA_BASE = "https://r.jina.ai/"
JINA_TIMEOUT = 15
# Max chars to send to Groq — enough context without blowing token budget
MAX_CONTENT_CHARS = 1500

# Phrases that indicate Jina hit a login wall instead of real content
BLOCKED_PHRASES = [
    "sign in",
    "log in",
    "login",
    "create an account",
    "join linkedin",
    "join now",
    "not available",
    "access denied",
    "captcha",
]


def _is_blocked(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in BLOCKED_PHRASES)


def fetch_content(url: str) -> str | None:
    """
    Fetch a URL via Jina Reader and return clean markdown content.
    Returns None if blocked, failed, or content is too short to be useful.
    """
    try:
        full_url = url if url.startswith("http") else f"https://{url}"
        jina_url = f"{JINA_BASE}{full_url}"
        resp = requests.get(
            jina_url,
            headers={"Accept": "text/plain"},
            timeout=JINA_TIMEOUT,
        )
        resp.raise_for_status()
        content = resp.text.strip()

        if not content or len(content) < 50:
            return None

        if _is_blocked(content[:500]):
            return None

        return content[:MAX_CONTENT_CHARS]

    except requests.RequestException:
        return None
