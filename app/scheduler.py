"""Scheduled monitoring via APScheduler."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .config import config

log = logging.getLogger(__name__)

_scheduler = None


def start_scheduler(scan_fn):
    """Start the background scheduler. Idempotent."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        scan_fn,
        trigger=IntervalTrigger(minutes=config.scan_interval_minutes),
        id="scan",
        name="apprenticeship-scan",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    log.info("Scheduler started: scan every %d minutes",
             config.scan_interval_minutes)
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
