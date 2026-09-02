"""Scan orchestration: run all sources, dedupe, store, alert."""
import logging
from datetime import datetime, timezone
from typing import List

from .config import config
from .db import Storage
from .sources import GovUKSource, EmployerPagesSource, LinkedInSource

log = logging.getLogger(__name__)


def _sources():
    return [GovUKSource(), EmployerPagesSource(), LinkedInSource()]


def run_scan(storage: Storage) -> dict:
    """Run every source, upsert into storage, mark closed, send alerts."""
    all_keys = []
    new_opps = []
    results = {"sources": {}, "new": 0, "updated": 0, "duplicates": 0}

    for source in _sources():
        opps = source.run()
        results["sources"][source.name] = len(opps)
        for opp in opps:
            all_keys.append(opp.dedup_key)
            outcome = storage.upsert(opp)
            results[outcome] = results.get(outcome, 0) + 1
            if outcome == "new":
                new_opps.append(opp)

    storage.mark_closed(all_keys)
    results["new"] = results.get("new", 0)
    results["active"] = storage.stats()["active"]

    # Alerts
    if config.alerts_configured:
        from .alerts import send_new_roles, send_deadline_alerts
        try:
            send_new_roles(storage, new_opps)
            send_deadline_alerts(storage)
        except Exception as exc:  # noqa: BLE001
            log.warning("Alert delivery failed: %s", exc)
    else:
        log.info("Alerts not configured; skipping WhatsApp delivery")

    log.info("Scan complete: %s", results)
    return results


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
