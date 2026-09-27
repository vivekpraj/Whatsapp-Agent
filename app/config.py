import os
from dotenv import load_dotenv

load_dotenv()

KAPSO_API_KEY = os.getenv("KAPSO_API_KEY")
KAPSO_PHONE_NUMBER_ID = os.getenv("KAPSO_PHONE_NUMBER_ID")
KAPSO_WEBHOOK_SECRET = os.getenv("KAPSO_WEBHOOK_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
USER_PHONE_NUMBER = os.getenv("USER_PHONE_NUMBER")
PORT = int(os.getenv("PORT", 5000))
