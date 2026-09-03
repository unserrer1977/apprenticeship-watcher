"""UK Apprenticeship Watcher — FastAPI app.

Runs a background scheduler that scans apprenticeship sources, stores results
in SQLite, alerts via WhatsApp, and serves a review dashboard.
"""
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

from .config import config
from .dashboard import render_dashboard
from .db import Storage
from .scheduler import start_scheduler, stop_scheduler
from .watcher import run_scan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("watcher")

storage = Storage()
_scan_lock = threading.Lock()


def _scan_job():
    if not _scan_lock.acquire(blocking=False):
        log.info("Scan already running; skipping")
        return
    try:
        run_scan(storage)
    finally:
        _scan_lock.release()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting Apprenticeship Watcher")
    start_scheduler(_scan_job)
    # Run an initial scan in the background so the dashboard is populated.
    threading.Thread(target=_scan_job, name="initial-scan", daemon=True).start()
    yield
    stop_scheduler()


app = FastAPI(title="Apprenticeship Watcher", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "active": storage.stats()["active"]}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    # Default view: prioritised (digital marketing / AI / business, degree,
    # major employers first), active roles.
    opps = storage.list(status="active", sort="priority")
    return HTMLResponse(render_dashboard(opps, storage.stats()))


@app.get("/api/opportunities")
def opportunities(
    region: str = Query("", description="manchester, leeds, nw, ..."),
    source: str = Query(""),
    status: str = Query("active"),
    topic: str = Query("", description="digital_marketing, ai, business"),
    min_priority: int = Query(0, description="only roles with priority >= this"),
    closing_soon: bool = Query(False),
    sort: str = Query("newest", description="newest, priority, deadline"),
):
    return storage.list(
        region=region or None,
        source=source or None,
        status=status or None,
        topic=topic or None,
        min_priority=min_priority or None,
        closing_soon=closing_soon,
        sort=sort,
    )


@app.get("/api/priority")
def priority_list(
    min_priority: int = Query(50),
    limit: int = Query(50, le=200),
):
    """Top-scoring opportunities (digital marketing / AI / business focus,
    degree apprenticeships and major employers weighted highest)."""
    return storage.list(status="active", min_priority=min_priority,
                        sort="priority")[:limit]


@app.get("/api/stats")
def stats():
    return storage.stats()


@app.get("/api/run")
def trigger_scan():
    """Trigger a scan synchronously (may take ~30s)."""
    _scan_job()
    return {"status": "ok", "stats": storage.stats()}


@app.get("/api/run-async")
def trigger_scan_async():
    threading.Thread(target=_scan_job, name="manual-scan", daemon=True).start()
    return {"status": "started"}


@app.exception_handler(Exception)
async def unhandled(exc):
    log.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"error": str(exc)})
