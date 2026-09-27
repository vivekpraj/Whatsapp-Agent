import hmac
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Patch the secret before importing app modules
TEST_SECRET = "test_webhook_secret"


@pytest.fixture
def client():
    with patch("app.config.KAPSO_WEBHOOK_SECRET", TEST_SECRET):
        with patch("app.security.KAPSO_WEBHOOK_SECRET", TEST_SECRET):
            from main import app
            return TestClient(app)


def make_signature(payload: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


# --- Health endpoint ---

def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- Signature validation ---

def test_valid_signature_accepted(client):
    payload = json.dumps({
        "event": "whatsapp.message.received",
        "data": {"from": "+911234567890", "type": "text", "text": {"body": "hello"}}
    }).encode()
    sig = make_signature(payload, TEST_SECRET)
    resp = client.post("/webhook", content=payload, headers={
        "Content-Type": "application/json",
        "x-kapso-signature": sig
    })
    assert resp.status_code == 200


def test_invalid_signature_rejected(client):
    payload = json.dumps({"event": "whatsapp.message.received", "data": {}}).encode()
    resp = client.post("/webhook", content=payload, headers={
        "Content-Type": "application/json",
        "x-kapso-signature": "sha256=invalidsignature"
    })
    assert resp.status_code == 401


def test_missing_signature_rejected(client):
    payload = json.dumps({"event": "whatsapp.message.received", "data": {}}).encode()
    resp = client.post("/webhook", content=payload, headers={
        "Content-Type": "application/json"
    })
    assert resp.status_code == 401


# --- Webhook routing ---

def test_non_message_event_ignored(client):
    payload = json.dumps({"event": "whatsapp.status.updated", "data": {}}).encode()
    sig = make_signature(payload, TEST_SECRET)
    resp = client.post("/webhook", content=payload, headers={
        "Content-Type": "application/json",
        "x-kapso-signature": sig
    })
    assert resp.status_code == 200


def test_non_text_message_ignored(client):
    payload = json.dumps({
        "event": "whatsapp.message.received",
        "data": {"from": "+911234567890", "type": "image", "text": {}}
    }).encode()
    sig = make_signature(payload, TEST_SECRET)
    resp = client.post("/webhook", content=payload, headers={
        "Content-Type": "application/json",
        "x-kapso-signature": sig
    })
    assert resp.status_code == 200


def test_text_message_returns_sender_and_text(client):
    payload = json.dumps({
        "event": "whatsapp.message.received",
        "data": {
            "from": "+911234567890",
            "type": "text",
            "text": {"body": "Hello bot!"}
        }
    }).encode()
    sig = make_signature(payload, TEST_SECRET)
    resp = client.post("/webhook", content=payload, headers={
        "Content-Type": "application/json",
        "x-kapso-signature": sig
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["received"] is True
    assert data["from"] == "+911234567890"
    assert data["text"] == "Hello bot!"
