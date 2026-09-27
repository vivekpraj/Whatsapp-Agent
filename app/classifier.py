import re

# Matches any URL: http/https or bare domains like github.com/user/repo
URL_PATTERN = re.compile(
    r"(https?://[^\s]+|(?:www\.)?[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)",
    re.IGNORECASE,
)

# Matches common reminder phrases
REMINDER_PATTERN = re.compile(
    r"\b(remind(er)?|remind me|set a reminder|alert me|notify me|wake me|ping me)\b"
    r"|(\bat\s+\d+(\:\d+)?\s*(am|pm)?\b)"
    r"|(\btomorrow\b|\btonight\b|\bmonday\b|\btuesday\b|\bwednesday\b"
    r"|\bthursday\b|\bfriday\b|\bsaturday\b|\bsunday\b)"
    r"|(\bnext\s+(week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b)"
    r"|(\bin\s+\d+\s*(hour|hours|hr|hrs|minute|minutes|min|mins|day|days)\b)",
    re.IGNORECASE,
)


def extract_url(text: str) -> str | None:
    """Return the first URL found in text, or None."""
    match = URL_PATTERN.search(text)
    return match.group(0) if match else None


def classify(text: str) -> str:
    """
    Returns one of: 'link' | 'reminder' | 'question'
    Priority: link > reminder > question
    """
    if URL_PATTERN.search(text):
        return "link"
    if REMINDER_PATTERN.search(text):
        return "reminder"
    return "question"
