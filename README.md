# Teams Bot

A small service that posts messages to a Microsoft Teams channel — on demand via a REST endpoint, or automatically on a cron schedule.

Uses the **Teams Workflow webhook** (Microsoft's current standard, replacing the deprecated Office 365 Connectors). No Azure app registration required.

---

## How it works

```
POST /send  ──────────────────────────────────────────▶  Teams channel
                                                         (via Workflow webhook)
Scheduler (cron) ────────────────────────────────────▶  Teams channel
```

---

## 1. Create the Teams webhook

1. Open the target Teams channel
2. Click **…** (More options) → **Workflows**
3. Search for **"Post to a channel when a webhook request is received"** and select it
4. Follow the prompts — name it, confirm the channel
5. Copy the **webhook URL** shown at the end (starts with `https://prod-...logic.azure.com/...`)

---

## 2. Setup

```bash
# 1. Clone or copy the folder
cd teams-bot

# 2. (Optional) create a virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
copy .env.example .env       # Windows
# cp .env.example .env        # macOS / Linux
```

Open `.env` and set at minimum:

```
TEAMS_WEBHOOK_URL=https://prod-xx.westeurope.logic.azure.com/workflows/...
```

---

## 3. Running

```bash
uvicorn main:app --reload
```

The service starts at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

## Endpoints

| Method | Path      | Description                              |
|--------|-----------|------------------------------------------|
| GET    | `/health` | Health check                             |
| POST   | `/send`   | Send a message to the Teams channel now  |

### `POST /send`

**Request body:**

```json
{
  "message": "Deployment finished successfully.",
  "title": "Release v2.1"
}
```

- `message` — required, the message body
- `title` — optional, shown in bold above the message

**Response:**

```json
{"status": "sent"}
```

### Example with curl

```bash
curl -X POST http://localhost:8000/send \
  -H "Content-Type: application/json" \
  -d '{"message": "Build passed!", "title": "CI Update"}'
```

---

## Scheduled messages

Set these three variables in `.env` to enable automatic scheduled messages:

| Variable           | Description                                          | Example               |
|--------------------|------------------------------------------------------|-----------------------|
| `SCHEDULE_CRON`    | Cron expression (minute hour day month weekday)      | `0 9 * * 1-5`         |
| `SCHEDULE_MESSAGE` | Message body to send on schedule                     | `Morning standup in 5 min!` |
| `SCHEDULE_TITLE`   | Optional bold title for the scheduled message        | `Daily Reminder`      |

**Common cron expressions:**

| Expression      | Meaning                    |
|-----------------|----------------------------|
| `0 9 * * 1-5`  | 9:00 AM every weekday      |
| `0 8 * * 1`    | 8:00 AM every Monday       |
| `0 17 * * 5`   | 5:00 PM every Friday       |
| `*/30 * * * *` | Every 30 minutes           |

If `SCHEDULE_CRON` or `SCHEDULE_MESSAGE` is empty, scheduling is disabled.

---

## Message appearance

Messages are sent as **Adaptive Cards**, which render in Teams like this:

```
┌─────────────────────────────┐
│  Release v2.1               │  ← title (bold, medium)
│  Deployment finished.       │  ← message (wrapped)
└─────────────────────────────┘
```

If no title is provided, only the message body is shown.