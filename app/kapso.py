import requests
from app.config import KAPSO_API_KEY, KAPSO_PHONE_NUMBER_ID

KAPSO_SEND_URL = "https://api.kapso.ai/v1/messages"


def send_reply(to: str, message: str) -> bool:
    """
    Send a WhatsApp text message to `to` via Kapso API.
    Returns True on success, False on failure.
    """
    headers = {
        "X-API-Key": KAPSO_API_KEY,
        "X-Phone-Number-Id": KAPSO_PHONE_NUMBER_ID,
        "Content-Type": "application/json",
    }
    payload = {
        "to": to,
        "type": "text",
        "text": {"body": message},
    }
    try:
        resp = requests.post(KAPSO_SEND_URL, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException:
        return False
