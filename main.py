from contextlib import asynccontextmanager
import logging

import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.config import PORT
from app.security import verify_signature
from app.classifier import classify
from app.kapso import send_reply
from app.handlers.link_handler import handle_link
from app.handlers.reminder_handler import handle_reminder
from app.handlers.qa_handler import handle_qa
from app.scheduler import start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="WhatsApp Personal AI Assistant", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


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
    msg_type = data.get("type", "")
    logger.info("msg_type: %s", msg_type)

    if msg_type != "text":
        return Response(status_code=200)

    text = data.get("text", {}).get("body", "").strip()
    sender = data.get("from", "")
    if sender and not sender.startswith("+"):
        sender = "+" + sender

    intent = classify(text)
    logger.info("Message from %s | intent: %s | text: %s", sender, intent, text)

    try:
        if intent == "link":
            reply = handle_link(text)
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
