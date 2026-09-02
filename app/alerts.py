"""WhatsApp alerts for new roles and approaching deadlines."""
import logging
from datetime import date, datetime
from typing import List

from .config import config
from .db import Storage
from .models import Opportunity

log = logging.getLogger(__name__)

try:
    from whatsmeow_client import WhatsAppClient
except Exception:  # noqa: BLE001
    WhatsAppClient = None


def _client():
    if WhatsAppClient is None:
        raise RuntimeError("whatsmeow_client not importable")
    return WhatsAppClient(
        base_url=config.whatsapp_base_url,
        api_key=config.whatsapp_api_key,
    )


def _fmt_date(iso: str) -> str:
    if not iso:
        return "n/a"
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y")
    except ValueError:
        return iso


def _role_line(opp: dict) -> str:
    parts = [opp.get("role") or "Role"]
    if opp.get("employer"):
        parts.append(opp["employer"])
    if opp.get("location"):
        parts.append(opp["location"])
    if opp.get("salary"):
        parts.append(opp["salary"])
    if opp.get("deadline"):
        parts.append(f"closes {_fmt_date(opp['deadline'])}")
    return " • ".join(parts)


def send_new_roles(storage: Storage, new_opps: List[Opportunity]):
    """Alert on newly discovered roles, then mark them alerted."""
    if not new_opps:
        return
    client = _client()
    lines = [f"🆕 {len(new_opps)} new apprenticeship role(s) in the North West:"]
    for opp in new_opps[:10]:
        lines.append(f"• {_role_line(opp.to_dict())}")
        lines.append(f"  {opp.application_link}")
    if len(new_opps) > 10:
        lines.append(f"…and {len(new_opps) - 10} more (see dashboard)")
    message = "\n".join(lines)
    _send(client, message)
    for opp in new_opps:
        storage.set_alerted(opp.id, "alerted_new")


def send_deadline_alerts(storage: Storage):
    """Alert on roles closing within the alert window, once each."""
    client = _client()
    today = date.today()
    window = config.deadline_alert_days
    due = []
    for opp in storage.unalerted_deadline(window):
        try:
            d = datetime.fromisoformat(opp["deadline"]).date()
        except (ValueError, TypeError):
            continue
        days_left = (d - today).days
        if 0 <= days_left <= window:
            due.append((opp, days_left))
    if not due:
        return
    due.sort(key=lambda x: x[1])
    lines = [f"⏰ {len(due)} apprenticeship deadline(s) approaching:"]
    for opp, days_left in due:
        urgency = "🔴" if days_left <= 2 else "🟠"
        lines.append(f"{urgency} {_role_line(opp)} ({days_left}d left)")
        lines.append(f"  {opp['application_link']}")
    _send(client, "\n".join(lines))
    for opp, _ in due:
        storage.set_alerted(opp["id"], "alerted_deadline")


def _send(client, message: str):
    resp = client.send_message(phone=config.whatsapp_phone, message=message)
    if not resp.get("success"):
        log.warning("WhatsApp send reported failure: %s", resp)
