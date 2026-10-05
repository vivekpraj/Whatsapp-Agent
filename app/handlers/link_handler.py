import json
import re
import requests as http_requests
from datetime import datetime
from urllib.parse import urlparse

import gspread
from google.oauth2.service_account import Credentials

from app.config import SHEET_ID, GOOGLE_SERVICE_ACCOUNT_JSON
from app.classifier import extract_url
from app.scraper import fetch_content
from app.llm import chat

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

LINK_TYPE_MAP = {
    "github.com": "github",
    "linkedin.com": "linkedin",
    "instagram.com": "instagram",
    "twitter.com": "article",
    "x.com": "article",
    "youtube.com": "article",
    "medium.com": "article",
    "substack.com": "article",
    "dev.to": "article",
    "hashnode.dev": "article",
}

# Fallback topics when Jina is blocked
FALLBACK_TOPICS = {
    "linkedin": "LinkedIn profile or post",
    "instagram": "Instagram post",
    "github": "GitHub repository",
    "article": "Article or video",
    "other": "Web link",
}


def _get_sheet():
    creds_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1


def classify_link_type(domain: str) -> str:
    """Return a category for the link based on its domain."""
    clean = domain.lower().lstrip("www.")
    for key, value in LINK_TYPE_MAP.items():
        if clean == key or clean.endswith("." + key):
            return value
    return "other"


def extract_domain(url: str) -> str:
    """Extract bare domain from a URL."""
    try:
        parsed = urlparse(url if "://" in url else "https://" + url)
        return parsed.netloc.lstrip("www.") or url
    except Exception:
        return url


def extract_note(text: str, url: str) -> str:
    """Return text surrounding the URL as a note."""
    return text.replace(url, "").strip()


def _generate_topic(content: str, url: str) -> str:
    """Summarize page content into a single topic line, stripping model reasoning."""
    import re as _re
    try:
        raw = chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You summarize web page content into a single short topic line "
                        "of at most 10 words. Output ONLY the topic line, no explanation, "
                        "no thinking, no markdown. Plain text only."
                    ),
                },
                {
                    "role": "user",
                    "content": f"URL: {url}\n\nContent:\n{content}",
                },
            ],
            max_tokens=200,
            temperature=0,
        )
        # Strip <think>...</think> blocks
        raw = _re.sub(r"<think>.*?</think>", "", raw, flags=_re.DOTALL).strip()
        # Strip lines that look like thinking preamble
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        for line in lines:
            lower = line.lower()
            if any(lower.startswith(p) for p in (
                "here's", "here is", "let me", "i need", "i will", "step", "1.", "•", "-"
            )):
                continue
            if len(line) < 150:
                return line
        return ""
    except Exception:
        return ""


def get_topic(url: str, link_type: str) -> str:
    """
    Try Jina Reader → LLM summarization.
    Falls back to a sensible default if blocked or failed.
    """
    content = fetch_content(url)
    if content and len(content) > 100:
        topic = _generate_topic(content, url)
        if topic:
            return topic
    return FALLBACK_TOPICS.get(link_type, "Web link")


# Pending links awaiting a user-supplied topic: {sender: {"url": url, "link_type": link_type, "note": note}}
_pending_links: dict[str, dict] = {}


def handle_link(text: str, sender: str) -> str:
    """
    Extract the URL and ask the user what topic to save it under.
    State is stored in _pending_links until the user replies.
    """
    url = extract_url(text)
    if not url:
        return "Could not find a link in your message."

    domain = extract_domain(url)
    link_type = classify_link_type(domain)
    note = extract_note(text, url)

    _pending_links[sender] = {"url": url, "link_type": link_type, "note": note}
    return "Got the link! What topic should I save it under?"


def save_link_with_topic(sender: str, topic: str) -> str:
    """
    Called when the user replies with a topic for their pending link.
    Saves to Sheets and clears pending state.
    """
    pending = _pending_links.pop(sender, None)
    if not pending:
        return None  # caller will fall through to QA handler

    url = pending["url"]
    link_type = pending["link_type"]
    note = pending["note"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = [timestamp, url, link_type, extract_domain(url), note, topic]
    sheet = _get_sheet()
    sheet.append_row(row, value_input_option="USER_ENTERED")

    type_label = link_type.capitalize()
    return f"Saved! {type_label} link tagged as: {topic}"


def has_pending_link(sender: str) -> bool:
    return sender in _pending_links
