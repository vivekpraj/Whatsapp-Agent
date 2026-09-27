import hmac
import hashlib
import logging
from app.config import KAPSO_WEBHOOK_SECRET

logger = logging.getLogger(__name__)


def verify_signature(payload_bytes: bytes, signature_header: str | None) -> bool:
    """Validate Kapso webhook HMAC-SHA256 signature."""
    if not KAPSO_WEBHOOK_SECRET:
        return True

    logger.info("Signature header received: %s", signature_header)

    if not signature_header:
        logger.warning("No signature header — rejecting")
        return False

    expected = hmac.new(
        KAPSO_WEBHOOK_SECRET.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    # Kapso sends raw hex (no "sha256=" prefix)
    received = signature_header.removeprefix("sha256=")
    match = hmac.compare_digest(expected, received)
    logger.info("Signature match: %s | expected: %s | received: %s", match, expected, received)
    return match
