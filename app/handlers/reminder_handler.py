import json
import logging
import re
from datetime import datetime

import pytz

from app.llm import chat
from app.scheduler import scheduler
from app.kapso import send_reply
from app.reminder_store import save_reminder, mark_done

IST = pytz.timezone("Asia/Kolkata")
logger = logging.getLogger(__name__)

PARSE_PROMPT = (
    "You are a JSON extraction tool. Output ONLY a single JSON object, no explanation, no thinking, no markdown.\n"
    "Today in IST: {now}.\n"
    "The user will give a reminder in natural language with 12-hour time (e.g. '11:55 pm', '6am', '3.30 PM').\n"
    "Convert to 24-hour ISO datetime. Examples: '11:55 pm' = 23:55, '6am' = 06:00, '3.30 PM' = 15:30.\n"
    "Output exactly:\n"
    '{{"datetime_ist": "YYYY-MM-DDTHH:MM", "task": "short task description"}}\n'
    "If time is unclear, set datetime_ist to null."
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
        max_tokens=600,
        temperature=0,
    )

    logger.info("LLM raw response: %s", raw)

    # Strip <think>...</think> blocks
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    # Find ALL JSON objects — take the LAST one (the model's final answer, not examples in thinking)
    all_matches = list(re.finditer(r"\{[^{}]*\}", raw, re.DOTALL))
    if not all_matches:
        logger.warning("No JSON found in LLM response")
        return None

    parsed = None
    for match in reversed(all_matches):
        try:
            candidate = json.loads(match.group())
            if candidate.get("datetime_ist") and candidate.get("task"):
                parsed = candidate
                break
        except json.JSONDecodeError:
            continue

    if not parsed:
        logger.warning("No valid JSON with datetime_ist+task found in LLM response")
        return None

    return parsed


def _fire_reminder(task: str, to: str, reminder_id: str = ""):
    send_reply(to, f"Reminder: {task}")
    if reminder_id:
        mark_done(reminder_id)


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

    reminder_id = save_reminder(run_dt, task, sender)

    scheduler.add_job(
        func=_fire_reminder,
        trigger="date",
        run_date=run_dt,
        args=[task, sender, reminder_id],
        misfire_grace_time=300,
    )

    formatted = run_dt.strftime("%I:%M %p, %d %b %Y")
    return f"Reminder set for {formatted}: {task}"
