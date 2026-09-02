# UK Apprenticeship Watcher

Continuously monitors UK apprenticeship opportunities across the official
**Find an apprenticeship (GOV.UK)** service plus configurable employer career
pages and LinkedIn, focused on **Northwest England (Manchester, Leeds and
surrounding cities)**.

Detects new openings, tracks application deadlines and upcoming programmes,
deduplicates listings, and alerts via **WhatsApp** when a new role appears or a
deadline is approaching. A built-in web dashboard makes every tracked
opportunity easy to review and act on.

## Features

- **Scheduled monitoring** — APScheduler runs a full scan every N minutes
  (default 30) inside the always-on Railway web process.
- **Persistent storage** — SQLite on a Railway volume (`/data`), so data
  survives redeploys and restarts.
- **Deduplication** — a stable `dedup_key` (source + employer + role + location
  + link) prevents duplicate listings across sources and scans.
- **Time-sensitive detection** — flags **new** roles and **closing soon**
  (deadline within N days) so you act before it's too late.
- **Alerts** — WhatsApp messages for new roles and approaching deadlines
  (via your existing whatsmeow service).
- **Review dashboard** — filterable web UI + JSON API of every tracked role.

## Sources

| Source | Status | Notes |
|---|---|---|
| GOV.UK Find an apprenticeship | ✅ Primary | Official, reliable, has closing dates + wages |
| Employer career pages | ⚙️ Best-effort | Configurable list of career-page URLs |
| LinkedIn | ⚙️ Optional | Needs a `LI_AT` session cookie in env |

The source layer is pluggable — add a new crawler by subclassing `Source` in
`app/sources/`.

## Quick start (local)

```bash
pip install -r requirements.txt
export DATA_DIR=./data
export WHATSAPP_BASE_URL=... WHATSAPP_API_KEY=... WHATSAPP_PHONE=...
uvicorn app.main:app --port 8080
```

Open http://localhost:8080 for the dashboard. A scan runs automatically at
startup and then on the schedule.

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | 8080 | HTTP port (Railway sets this) |
| `DATA_DIR` | `/data` | Persistent data directory |
| `LOCATIONS` | Manchester,Leeds,Liverpool,Sheffield,Bradford,Preston,Warrington,Bolton,Salford,Huddersfield | Cities to search |
| `DISTANCE` | 15 | Search radius in miles |
| `SCAN_INTERVAL_MINUTES` | 30 | How often to scan |
| `DEADLINE_ALERT_DAYS` | 7 | Alert when deadline within this many days |
| `ALERT_ENABLED` | true | Master switch for WhatsApp alerts |
| `WHATSAPP_BASE_URL` | — | whatsmeow service URL |
| `WHATSAPP_API_KEY` | — | whatsmeow API key |
| `WHATSAPP_PHONE` | — | WhatsApp number to alert (E.164, no `+`) |
| `LI_AT` | — | Optional LinkedIn session cookie |
| `EMPLOYER_PAGES` | `[]` | JSON list of employer career-page URLs |

## API

- `GET /` — dashboard
- `GET /api/opportunities` — all tracked roles (JSON)
- `GET /api/opportunities?region=manchester&status=active&closing_soon=1`
- `GET /api/stats` — counts and source breakdown
- `GET /api/run` — trigger a scan now
- `GET /health` — health check
