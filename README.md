# UK Apprenticeship Watcher

Monitors UK apprenticeship opportunities from the official **Find an
apprenticeship (GOV.UK)** service and **Higherin (RateMyApprenticeship)**.
By default it tracks **only apprenticeships from major employers** (KPMG,
Deloitte, PwC, EY, Unilever, UBS, Siemens and many more), including their
degree apprenticeships — local and non-major firms are excluded.

Detects new openings, tracks application deadlines and upcoming programmes,
deduplicates listings, and alerts via **WhatsApp** when a new role appears or a
deadline is approaching. A built-in web dashboard makes every tracked
opportunity easy to review and act on.

## Features

- **Big-firm only scope** — with `ONLY_MAJOR_FIRMS=true` (the default) the
  watcher tracks **only apprenticeships from major employers**; every non-major
  firm is dropped, so local/small-firm roles are excluded entirely.
- **Scheduled monitoring** — APScheduler runs a full scan every N minutes
  (default 30) inside the always-on Railway web process.
- **Persistent storage** — SQLite on a Railway volume (`/data`), so data
  survives redeploys and restarts.
- **Priority scoring** — every role is scored 0-100 for how well it matches
  the watcher's focus: **digital marketing, AI/data, and business** topics,
  **degree apprenticeships** (level 6/7), and hiring by **major employers**
  (KPMG, Deloitte, PwC, EY, Unilever, UBS, Siemens and many more).
  High-priority roles rank at the top of the dashboard and are spotlighted
  first in alerts.
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
| Higherin (RateMyApprenticeship) | ✅ Primary (big-firm) | KPMG, Deloitte, PwC, EY, UBS, Unilever + degree apprenticeships |
| GOV.UK Find an apprenticeship | ✅ Secondary | Official, reliable, has closing dates + wages |
| Employer career pages | ⚙️ Best-effort | Configurable list of career-page URLs |
| LinkedIn | ⚙️ Optional | Needs a `LI_AT` session cookie in env |

The source layer is pluggable — add a new crawler by subclassing `Source` in
`app/sources/`.

## Major-employer allowlist

With `ONLY_MAJOR_FIRMS=true`, only roles whose employer matches the allowlist in
`app/scoring.py` (`_MAJOR_EMPLOYERS`) are tracked. Covered sectors: the Big 4
and professional services (KPMG, Deloitte, PwC, EY, Accenture, McKinsey, law
firms), investment banks and big finance (Goldman, Barclays, HSBC, Lloyds,
UBS, ...), tech (Microsoft, Amazon, Google, ...), telecom/media (BT, Sky, BBC,
ITV, ...), energy/utilities (BP, Shell, National Grid, E.ON, EDF, Siemens, ...),
aerospace/engineering/auto (BAE, Rolls-Royce, Airbus, BMW, ...), FMCG/pharma
(Unilever, GSK, AstraZeneca, ...) and broad services (Capita, Serco, ...).
Add a firm to the list to include it.

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
| `ONLY_MAJOR_FIRMS` | `true` | Track only apprenticeships from major employers |
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
| `HIGHERIN_ENABLED` | `true` | Enable the Higherin (RateMyApprenticeship) source |
| `HIGHERIN_ROUTES` | `["degree-apprenticeship","apprenticeships"]` | Higherin search routes |

## API

- `GET /` — dashboard (sorted by priority; score, topic, degree & major-employer
  badges)
- `GET /api/opportunities` — all tracked roles (JSON)
- `GET /api/opportunities?region=manchester&status=active&closing_soon=1&topic=ai&min_priority=50&sort=priority`
- `GET /api/priority` — top-scoring roles (digital marketing / AI / business
  focus, degree apprenticeships and major employers weighted highest)
- `GET /api/stats` — counts and source breakdown
- `GET /api/run` — trigger a scan now
- `GET /health` — health check