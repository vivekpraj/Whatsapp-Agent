import json
import logging
import re
from datetime import datetime

import pytz

from app.config import USER_PHONE_NUMBER
from app.llm import chat
from app.scheduler import scheduler
from app.kapso import send_reply

IST = pytz.timezone("Asia/Kolkata")
logger = logging.getLogger(__name__)

PARSE_PROMPT = (
    "You are a JSON extraction tool. Output ONLY a single JSON object, no explanation, no thinking, no markdown.\n"
    "Today in IST: {now}.\n"
    "Extract the reminder from the user message and output exactly:\n"
    '{{"datetime_ist": "2026-09-28T10:00", "task": "mail a client"}}\n'
    "Use the real date and time values. If time is unclear, set datetime_ist to null."
)


def _parse_reminder_with_gemini(text: str) -> dict | None:
    """
    Call Gemini to extract datetime and task from natural language.
    Returns {"datetime_ist": "YYYY-MM-DDTHH:mm", "task": "..."} or None on failure.
    """
    now_str = datetime.now(IST).strftime("%Y-%m-%d %H:%M")
    system_prompt = PARSE_PROMPT.format(now=now_str)

    raw = chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        max_tokens=100,
        temperature=0,
    )

    logger.info("LLM raw response: %s", raw)

    # Strip <think>...</think> blocks from reasoning models
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    # Extract JSON block
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_match:
        logger.warning("No JSON found in LLM response")
        return None

    parsed = json.loads(json_match.group())
    if not parsed.get("datetime_ist") or not parsed.get("task"):
        return None

    return parsed


def _fire_reminder(task: str, to: str):
    send_reply(to, f"Reminder: {task}")


def handle_reminder(text: str, sender: str) -> str:
    """
    Parse the reminder from natural language, schedule it,
    and return a confirmation reply string.
    """
    parsed = _parse_reminder_with_gemini(text)

    if not parsed:
        return "Sorry, I could not understand the reminder time. Try: 'Remind me at 6pm to call John'."

    run_dt = datetime.strptime(parsed["datetime_ist"], "%Y-%m-%dT%H:%M")
    run_dt = IST.localize(run_dt)
    task = parsed["task"]

    if run_dt <= datetime.now(IST):
        return "That time has already passed. Please set a future reminder."

    scheduler.add_job(
        func=_fire_reminder,
        trigger="date",
        run_date=run_dt,
        args=[task, sender],
        misfire_grace_time=60,
    )

    formatted = run_dt.strftime("%I:%M %p, %d %b %Y")
    return f"Reminder set for {formatted}: {task}"
