import csv
import os
import logging
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

WEBHOOK_URL = os.environ["TEAMS_WEBHOOK_URL"]
SCHEDULE_CRON = os.getenv("SCHEDULE_CRON", "")
SCHEDULE_TITLE = os.getenv("SCHEDULE_TITLE", "Good morning!")

_GREETINGS: list[tuple[str, str]] = []
_csv_path = Path(__file__).parent / "assets" / "good-morning-in-140-languages.csv"
with _csv_path.open(encoding="utf-8") as _f:
    for _row in csv.DictReader(_f, delimiter=";"):
        _GREETINGS.append((_row["language"], _row["good-morning"]))
log.info("Loaded %d greetings from CSV", len(_GREETINGS))


def _todays_greeting() -> tuple[str, str]:
    idx = date.today().timetuple().tm_yday % len(_GREETINGS)
    return _GREETINGS[idx]


def _build_payload(message: str, title: str | None = None) -> dict:
    body = []
    if title:
        body.append({"type": "TextBlock", "text": title, "weight": "Bolder", "size": "Medium"})
    body.append({"type": "TextBlock", "text": message, "wrap": True})
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.2",
                    "body": body,
                },
            }
        ],
    }


def send_to_teams(message: str, title: str | None = None, webhook_url: str | None = None) -> None:
    target = webhook_url or WEBHOOK_URL
    payload = _build_payload(message, title or None)
    log.info("Sending message | title=%r | preview=%r | target=%s", title, message[:80], target)
    resp = httpx.post(target, json=payload, timeout=15)
    resp.raise_for_status()
    log.info("Message sent successfully | status=%d | target=%s", resp.status_code, target)


def _scheduled_job() -> None:
    language, greeting = _todays_greeting()
    message = f"{greeting} in {language}"
    try:
        send_to_teams(message, SCHEDULE_TITLE or None)
        log.info("Scheduled message sent | language=%s | greeting=%s", language, greeting)
    except Exception as exc:
        log.error("Scheduled send failed: %s", exc)


scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if SCHEDULE_CRON:
        scheduler.add_job(_scheduled_job, CronTrigger.from_crontab(SCHEDULE_CRON))
        scheduler.start()
        log.info("Scheduler started with cron: %s", SCHEDULE_CRON)
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Teams Bot", lifespan=lifespan)


class SendRequest(BaseModel):
    message: str
    title: str | None = None
    webhook_url: str | None = None  # override to target a different group or chat


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/send")
def send(req: SendRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")
    try:
        send_to_teams(req.message, req.title, req.webhook_url)
        return {"status": "sent"}
    except httpx.HTTPStatusError as exc:
        log.error("Teams rejected the message | status=%d | body=%s", exc.response.status_code, exc.response.text[:200])
        raise HTTPException(status_code=502, detail=f"Teams returned {exc.response.status_code}")
    except Exception as exc:
        log.error("Unexpected error sending message: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))