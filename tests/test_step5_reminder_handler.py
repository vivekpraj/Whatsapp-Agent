import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytz

IST = pytz.timezone("Asia/Kolkata")

FUTURE_DT = (datetime.now(IST) + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")
PAST_DT   = (datetime.now(IST) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")


def _mock_groq_response(datetime_ist: str, task: str):
    """Build a fake Groq API response."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps({"datetime_ist": datetime_ist, "task": task})
            }
        }]
    }
    return mock_resp


# --- Groq parsing ---

@patch("app.handlers.reminder_handler.requests.post")
def test_future_reminder_scheduled(mock_post):
    mock_post.return_value = _mock_groq_response(FUTURE_DT, "Call John")

    with patch("app.handlers.reminder_handler.scheduler") as mock_scheduler:
        from app.handlers.reminder_handler import handle_reminder
        reply = handle_reminder("Remind me in 3 hours to call John", "+911234567890")

    assert mock_scheduler.add_job.called
    assert "Call John" in reply
    assert "Reminder set" in reply


@patch("app.handlers.reminder_handler.requests.post")
def test_past_reminder_rejected(mock_post):
    mock_post.return_value = _mock_groq_response(PAST_DT, "Submit report")

    from app.handlers.reminder_handler import handle_reminder
    reply = handle_reminder("Remind me an hour ago to submit report", "+911234567890")

    assert "already passed" in reply.lower()


@patch("app.handlers.reminder_handler.requests.post")
def test_groq_returns_null_datetime(mock_post):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": '{"datetime_ist": null, "task": "something"}'}}]
    }
    mock_post.return_value = mock_resp

    from app.handlers.reminder_handler import handle_reminder
    reply = handle_reminder("Remind me sometime", "+911234567890")

    assert "could not understand" in reply.lower()


@patch("app.handlers.reminder_handler.requests.post")
def test_groq_returns_invalid_json(mock_post):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "I cannot determine the time."}}]
    }
    mock_post.return_value = mock_resp

    from app.handlers.reminder_handler import handle_reminder
    reply = handle_reminder("blah blah blah", "+911234567890")

    assert "could not understand" in reply.lower()


@patch("app.handlers.reminder_handler.requests.post")
def test_groq_json_in_markdown_fence_parsed(mock_post):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content":
            f'```json\n{{"datetime_ist": "{FUTURE_DT}", "task": "gym"}}\n```'
        }}]
    }
    mock_post.return_value = mock_resp

    with patch("app.handlers.reminder_handler.scheduler"):
        from app.handlers.reminder_handler import handle_reminder
        reply = handle_reminder("Remind me in 3 hours to go to gym", "+911234567890")

    assert "gym" in reply.lower()


# --- Scheduler job ---

@patch("app.handlers.reminder_handler.requests.post")
def test_scheduler_add_job_called_with_correct_args(mock_post):
    mock_post.return_value = _mock_groq_response(FUTURE_DT, "Review the PR")

    with patch("app.handlers.reminder_handler.scheduler") as mock_scheduler:
        from app.handlers.reminder_handler import handle_reminder
        handle_reminder("Remind me in 3 hours to review the PR", "+911234567890")

    call_kwargs = mock_scheduler.add_job.call_args[1]
    assert call_kwargs["trigger"] == "date"
    assert "Review the PR" in call_kwargs["args"]


# --- Scheduler module ---

def test_scheduler_starts_and_stops():
    from app.scheduler import start_scheduler, shutdown_scheduler, scheduler
    start_scheduler()
    assert scheduler.running
    shutdown_scheduler()
    assert not scheduler.running


def test_start_scheduler_idempotent():
    from app.scheduler import start_scheduler, shutdown_scheduler, scheduler
    start_scheduler()
    start_scheduler()   # second call should not raise
    assert scheduler.running
    shutdown_scheduler()
