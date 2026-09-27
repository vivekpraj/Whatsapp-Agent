# WhatsApp Personal AI Assistant

A personal AI assistant that runs on WhatsApp. Send it a link, a question, or a reminder — it handles all three.

## Features

- **Link saving** — Send any URL and it gets saved to Google Sheets with timestamp, type, domain, note, and an AI-generated topic summary
- **Reminders** — Natural language reminders ("remind me at 6pm to call John") parsed by AI and fired back to you on WhatsApp at the right time
- **Q&A** — Ask anything and get a concise 1-3 sentence answer

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI + Uvicorn |
| WhatsApp | Kapso BSP |
| AI / LLM | Google Gemini 2.0 Flash (free) |
| Link scraping | Jina Reader (r.jina.ai) |
| Storage | Google Sheets via Service Account |
| Scheduler | APScheduler (IST timezone) |
| Hosting | Render (free tier) |

## Project Structure

```
app/
├── config.py          # env var loader
├── security.py        # HMAC-SHA256 webhook signature validation
├── classifier.py      # intent detection (link / reminder / question)
├── kapso.py           # WhatsApp reply sender
├── llm.py             # Gemini API wrapper with 429 retry
├── scraper.py         # Jina Reader URL content fetcher
├── scheduler.py       # APScheduler singleton
└── handlers/
    ├── link_handler.py     # save link + AI topic to Google Sheets
    ├── reminder_handler.py # parse & schedule reminders
    └── qa_handler.py       # answer questions
main.py                # FastAPI app entry point
tests/                 # 101 pytest tests, all passing
```

## Environment Variables

Create a `.env` file in the project root:

```
KAPSO_API_KEY=
KAPSO_PHONE_NUMBER_ID=
KAPSO_WEBHOOK_SECRET=
GEMINI_API_KEY=
SHEET_ID=
GOOGLE_SERVICE_ACCOUNT_JSON=
USER_PHONE_NUMBER=
PORT=5000
```

## Setup

### 1. Clone & install

```bash
git clone https://github.com/vivekpraj/Whatsapp-Agent.git
cd Whatsapp-Agent
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 2. Get your API keys

- **Kapso** — [kapso.ai](https://kapso.ai) → connect a US number → copy API key
- **Gemini** — [aistudio.google.com](https://aistudio.google.com) → Get API Key (free, no card)
- **Google Sheets** — Create a sheet, set up a GCP Service Account with Sheets + Drive API enabled, share the sheet with the service account email, paste the JSON key as `GOOGLE_SERVICE_ACCOUNT_JSON` (single line)

### 3. Run locally

```bash
uvicorn main:app --reload --port 5000
```

### 4. Deploy to Render

- Push to GitHub
- New Web Service on [render.com](https://render.com) → connect repo
- Set all env vars in Render dashboard
- After deploy, register your Render URL as the Kapso webhook → copy the signing secret into `KAPSO_WEBHOOK_SECRET`

## Running Tests

```bash
pytest tests/ -v
```

101 tests, all external APIs mocked.

## How It Works

1. You send a WhatsApp message to your Kapso number
2. Kapso forwards it to your `/webhook` endpoint on Render
3. The classifier detects the intent (link / reminder / question)
4. The right handler processes it and sends a reply back via Kapso

**Link flow:** URL detected → Jina Reader scrapes the page → Gemini summarizes into a topic → row saved to Google Sheets → reply sent

**Reminder flow:** Gemini parses the datetime from natural language → APScheduler fires a WhatsApp message at the right time

**Q&A flow:** Gemini answers in 1-3 plain-text sentences → reply sent
