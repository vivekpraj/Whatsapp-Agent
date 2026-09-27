import logging
import requests
from app.config import KAPSO_API_KEY, KAPSO_PHONE_NUMBER_ID

logger = logging.getLogger(__name__)


def send_reply(to: str, message: str) -> bool:
    url = f"https://api.kapso.ai/meta/whatsapp/v24.0/{KAPSO_PHONE_NUMBER_ID}/messages"
    headers = {
        "X-API-Key": KAPSO_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        logger.info("Kapso send status: %s | to: %s | response: %s", resp.status_code, to, resp.text)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error("Kapso send failed: %s", e)
        return False
