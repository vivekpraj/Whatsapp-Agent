from contextlib import asynccontextmanager
import logging

import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Deduplication: track recently processed message IDs (max 500)
_seen_ids: set[str] = set()
_seen_ids_order: list[str] = []

from app.config import PORT
from app.security import verify_signature
from app.classifier import classify
from app.kapso import send_reply
from app.handlers.link_handler import handle_link, has_pending_link, save_link_with_topic
from app.handlers.reminder_handler import handle_reminder, _fire_reminder
from app.handlers.qa_handler import handle_qa
from app.scheduler import start_scheduler, shutdown_scheduler
from app.reminder_store import load_pending


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    # Reload reminders that survived a server restart
    try:
        from app.scheduler import scheduler
        pending = load_pending()
        for r in pending:
            scheduler.add_job(
                func=_fire_reminder,
                trigger="date",
                run_date=r["run_dt"],
                args=[r["task"], r["phone"], r["reminder_id"]],
                misfire_grace_time=300,
            )
        if pending:
            logger.info("Reloaded %d pending reminder(s) from Sheets", len(pending))
    except Exception:
        logger.exception("Failed to reload reminders on startup")
    yield
    shutdown_scheduler()


app = FastAPI(title="WhatsApp Personal AI Assistant", lifespan=lifespan)


@app.get("/health")
async def health():
    return Response(content="ok", media_type="text/plain")


@app.post("/webhook")
async def webhook(request: Request):
    payload_bytes = await request.body()
    logger.info("Incoming headers: %s", dict(request.headers))
    signature = request.headers.get("x-webhook-signature")

    if not verify_signature(payload_bytes, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        import json as _json
        body = _json.loads(payload_bytes) if payload_bytes else {}
    except Exception as e:
        logger.exception("Failed to parse body: %s", e)
        body = {}

    logger.info("Body: %s", body)

    # v2 payload: event is in the x-webhook-event header, not body
    event = request.headers.get("x-webhook-event", body.get("event", ""))

    if event != "whatsapp.message.received":
        logger.info("Ignoring event: %s", event)
        return Response(status_code=200)

    # Kapso v2 payload: message is under body["message"]
    data = body.get("message", body.get("data", {}))

    # Deduplicate: skip if we already processed this message ID
    msg_id = data.get("id", "")
    if msg_id and msg_id in _seen_ids:
        logger.info("Duplicate message %s — skipping", msg_id)
        return Response(status_code=200)
    if msg_id:
        _seen_ids.add(msg_id)
        _seen_ids_order.append(msg_id)
        if len(_seen_ids_order) > 500:
            _seen_ids.discard(_seen_ids_order.pop(0))

    msg_type = data.get("type", "")
    logger.info("msg_type: %s", msg_type)

    if msg_type != "text":
        return Response(status_code=200)

    text = data.get("text", {}).get("body", "").strip()
    sender = data.get("from", "")
    if sender and not sender.startswith("+"):
        sender = "+" + sender

    # If sender has a pending link, their reply is the topic — save immediately
    if has_pending_link(sender):
        logger.info("Message from %s | pending link topic: %s", sender, text)
        try:
            reply = save_link_with_topic(sender, text.strip())
            if reply is None:
                reply = handle_qa(text)
        except Exception as e:
            logger.exception("Error saving link with topic: %s", e)
            reply = "Sorry, something went wrong saving your link."
        logger.info("Reply: %s", reply)
        send_reply(sender, reply)
        return {"received": True, "from": sender, "text": text, "intent": "link_topic", "reply": reply}

    intent = classify(text)
    logger.info("Message from %s | intent: %s | text: %s", sender, intent, text)

    try:
        if intent == "link":
            reply = handle_link(text, sender)
        elif intent == "reminder":
            reply = handle_reminder(text, sender)
        else:
            reply = handle_qa(text)
    except Exception as e:
        logger.exception("Handler error for intent=%s: %s", intent, e)
        reply = "Sorry, something went wrong on my end."

    logger.info("Reply: %s", reply)
    send_reply(sender, reply)

    return {"received": True, "from": sender, "text": text, "intent": intent, "reply": reply}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
