import logging
import requests
from app.config import KAPSO_API_KEY, KAPSO_PHONE_NUMBER_ID

KAPSO_SEND_URL = "https://api.kapso.ai/v1/messages"
logger = logging.getLogger(__name__)


def send_reply(to: str, message: str) -> bool:
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
        logger.info("Kapso send status: %s | to: %s | response: %s", resp.status_code, to, resp.text)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error("Kapso send failed: %s", e)
        return False
