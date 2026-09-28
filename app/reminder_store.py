"""
Persistent reminder storage using a dedicated Google Sheets tab.
Columns: reminder_id | datetime_ist | task | phone | status
"""
import json
import uuid
import logging
from datetime import datetime

import gspread
import pytz
from google.oauth2.service_account import Credentials

from app.config import SHEET_ID, GOOGLE_SERVICE_ACCOUNT_JSON

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADER = ["reminder_id", "datetime_ist", "task", "phone", "status"]


def _get_sheet():
    creds_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_ID)
    try:
        ws = spreadsheet.worksheet("Reminders")
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title="Reminders", rows=1000, cols=5)
        ws.append_row(HEADER)
    return ws


def save_reminder(run_dt: datetime, task: str, phone: str) -> str:
    """Persist a reminder row and return its reminder_id."""
    rid = str(uuid.uuid4())
    dt_str = run_dt.strftime("%Y-%m-%dT%H:%M")
    try:
        ws = _get_sheet()
        ws.append_row([rid, dt_str, task, phone, "pending"])
    except Exception:
        logger.exception("Failed to save reminder to Sheets")
    return rid


def mark_done(reminder_id: str):
    """Update status to 'done' for the given reminder_id."""
    try:
        ws = _get_sheet()
        cell = ws.find(reminder_id)
        if cell:
            ws.update_cell(cell.row, 5, "done")
    except Exception:
        logger.exception("Failed to mark reminder done: %s", reminder_id)


def load_pending() -> list[dict]:
    """Return all pending reminders that are still in the future."""
    now = datetime.now(IST)
    results = []
    try:
        ws = _get_sheet()
        rows = ws.get_all_records()
        for row in rows:
            if row.get("status") != "pending":
                continue
            try:
                run_dt = IST.localize(datetime.strptime(row["datetime_ist"], "%Y-%m-%dT%H:%M"))
            except Exception:
                continue
            if run_dt > now:
                results.append({
                    "reminder_id": row["reminder_id"],
                    "run_dt": run_dt,
                    "task": row["task"],
                    "phone": row["phone"],
                })
            else:
                # Mark past-due reminders as missed
                try:
                    cell = ws.find(row["reminder_id"])
                    if cell:
                        ws.update_cell(cell.row, 5, "missed")
                except Exception:
                    pass
    except Exception:
        logger.exception("Failed to load pending reminders")
    return results
