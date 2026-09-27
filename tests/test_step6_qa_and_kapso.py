import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import hmac
import hashlib

TEST_SECRET = "test_webhook_secret"


def make_signature(payload: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


# ── Q&A handler ──────────────────────────────────────────────────────────────

def _mock_groq(answer: str):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": answer}}]
    }
    return mock_resp


@patch("app.handlers.qa_handler.requests.post")
def test_qa_returns_groq_answer(mock_post):
    mock_post.return_value = _mock_groq("The capital of France is Paris.")
    from app.handlers.qa_handler import handle_qa
    reply = handle_qa("What is the capital of France?")
    assert reply == "The capital of France is Paris."


@patch("app.handlers.qa_handler.requests.post")
def test_qa_strips_whitespace(mock_post):
    mock_post.return_value = _mock_groq("  Hello!  ")
    from app.handlers.qa_handler import handle_qa
    reply = handle_qa("Say hello")
    assert reply == "Hello!"


@patch("app.handlers.qa_handler.requests.post")
def test_qa_network_error_returns_friendly_message(mock_post):
    import requests as req
    mock_post.side_effect = req.RequestException("timeout")
    from app.handlers.qa_handler import handle_qa
    reply = handle_qa("Anything")
    assert "could not reach" in reply.lower()


@patch("app.handlers.qa_handler.requests.post")
def test_qa_bad_response_shape_returns_friendly_message(mock_post):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"unexpected": "shape"}
    mock_post.return_value = mock_resp
    from app.handlers.qa_handler import handle_qa
    reply = handle_qa("Anything")
    assert "unexpected response" in reply.lower()


# ── Kapso send_reply ──────────────────────────────────────────────────────────

@patch("app.kapso.requests.post")
def test_send_reply_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp
    from app.kapso import send_reply
    result = send_reply("+911234567890", "Hello!")
    assert result is True
    call_payload = mock_post.call_args[1]["json"]
    assert call_payload["to"] == "+911234567890"
    assert call_payload["text"]["body"] == "Hello!"
    assert call_payload["type"] == "text"


@patch("app.kapso.requests.post")
def test_send_reply_failure_returns_false(mock_post):
    import requests as req
    mock_post.side_effect = req.RequestException("network error")
    from app.kapso import send_reply
    result = send_reply("+911234567890", "Hello!")
    assert result is False


# ── End-to-end webhook → Q&A → Kapso reply ───────────────────────────────────

@pytest.fixture
def client():
    with patch("app.config.KAPSO_WEBHOOK_SECRET", TEST_SECRET):
        with patch("app.security.KAPSO_WEBHOOK_SECRET", TEST_SECRET):
            from main import app
            return TestClient(app)


def test_e2e_question_triggers_groq_and_kapso_reply(client):
    kapso_mock = MagicMock()
    kapso_mock.raise_for_status = MagicMock()

    with patch("main.handle_qa", return_value="42 is the answer."):
        with patch("app.kapso.requests.post", return_value=kapso_mock) as mock_kapso_call:
            payload = json.dumps({
                "event": "whatsapp.message.received",
                "data": {
                    "from": "+911234567890",
                    "type": "text",
                    "text": {"body": "What is the answer to life?"}
                }
            }).encode()
            sig = make_signature(payload, TEST_SECRET)

            resp = client.post("/webhook", content=payload, headers={
                "Content-Type": "application/json",
                "x-kapso-signature": sig,
            })

    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "question"
    assert data["reply"] == "42 is the answer."
    assert mock_kapso_call.called


def test_e2e_link_saves_to_sheets_and_sends_kapso_reply(client):
    kapso_mock = MagicMock()
    kapso_mock.raise_for_status = MagicMock()

    with patch("app.handlers.link_handler._get_sheet", return_value=MagicMock()):
        with patch("app.kapso.requests.post", return_value=kapso_mock) as mock_kapso_call:
            payload = json.dumps({
                "event": "whatsapp.message.received",
                "data": {
                    "from": "+911234567890",
                    "type": "text",
                    "text": {"body": "https://github.com/user/repo"}
                }
            }).encode()
            sig = make_signature(payload, TEST_SECRET)

            resp = client.post("/webhook", content=payload, headers={
                "Content-Type": "application/json",
                "x-kapso-signature": sig,
            })

    assert resp.status_code == 200
    assert resp.json()["intent"] == "link"
    assert mock_kapso_call.called
