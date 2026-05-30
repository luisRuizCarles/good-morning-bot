"""Standalone script used by GitHub Actions to send the daily greeting."""
import csv
import os
import httpx
from datetime import date
from pathlib import Path

greetings: list[tuple[str, str]] = []
with open(Path(__file__).parent / "assets" / "good-morning-in-140-languages.csv", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f, delimiter=";"):
        greetings.append((row["language"], row["good-morning"]))

language, greeting = greetings[date.today().timetuple().tm_yday % len(greetings)]
message = f"\"{greeting}\" in {language}"
title = os.getenv("SCHEDULE_TITLE", "Good morning!")
webhook_url = os.environ["TEAMS_WEBHOOK_URL"]

payload = {
    "type": "message",
    "attachments": [
        {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.2",
                "body": [
                    {"type": "TextBlock", "text": title, "weight": "Bolder", "size": "Medium"},
                    {"type": "TextBlock", "text": message, "wrap": True},
                ],
            },
        }
    ],
}

resp = httpx.post(webhook_url, json=payload, timeout=15)
resp.raise_for_status()
print(f"Sent: {message}")
