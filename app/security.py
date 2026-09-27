import hmac
import hashlib
from app.config import KAPSO_WEBHOOK_SECRET


def verify_signature(payload_bytes: bytes, signature_header: str | None) -> bool:
    """Validate Kapso webhook HMAC-SHA256 signature."""
    if not KAPSO_WEBHOOK_SECRET:
        # If no secret configured, skip validation (dev mode)
        return True

    if not signature_header:
        return False

    # Kapso sends: "sha256=<hex_digest>"
    prefix = "sha256="
    if not signature_header.startswith(prefix):
        return False

    expected = hmac.new(
        KAPSO_WEBHOOK_SECRET.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    received = signature_header[len(prefix):]
    return hmac.compare_digest(expected, received)
