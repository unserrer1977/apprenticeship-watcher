"""HTML dashboard rendering."""
from datetime import date, datetime
from html import escape

from .config import config

REGION_LABELS = {
    "manchester": "Manchester",
    "leeds": "Leeds",
    "liverpool": "Liverpool",
    "sheffield": "Sheffield",
    "nw": "North West",
    "other": "Other",
}

SOURCE_LABELS = {
    "govuk": "GOV.UK",
    "employer": "Employer",
    "linkedin": "LinkedIn",
}


def _days_to_deadline(deadline: str):
    if not deadline:
        return None
    try:
        d = datetime.fromisoformat(deadline).date()
        return (d - date.today()).days
    except (ValueError, TypeError):
        return None


def _fmt(iso: str) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y")
    except ValueError:
        return iso


def _is_new(first_seen: str) -> bool:
    if not first_seen:
        return False
    try:
        d = datetime.fromisoformat(first_seen).date()
        return (date.today() - d).days <= 7
    except (ValueError, TypeError):
        return False


def render_dashboard(opps: list, stats: dict) -> str:
    rows = []
    for o in opps:
        days = _days_to_deadline(o.get("deadline"))
        new = _is_new(o.get("first_seen"))
        badges = []
        if new:
            badges.append('<span class="badge badge-new">NEW</span>')
        if days is not None and 0 <= days <= config.deadline_alert_days:
            badges.append(
                f'<span class="badge badge-close">CLOSES {days}d</span>'
            )
        elif days is not None and days < 0:
            badges.append('<span class="badge badge-closed">CLOSED</span>')
        region = REGION_LABELS.get(o.get("region"), o.get("region") or "—")
        source = SOURCE_LABELS.get(o.get("source"), o.get("source"))
        rows.append(f"""
        <tr class="{'row-closed' if o.get('status') == 'closed' else ''}">
          <td class="role">
            <a href="{escape(o.get('application_link') or '#')}" target="_blank"
               rel="noopener">{escape(o.get('role') or '—')}</a>
            <div class="sub">{escape(o.get('employer') or '')}</div>
          </td>
          <td>{escape(o.get('location') or '—')}</td>
          <td><span class="pill pill-{escape(o.get('region') or 'other')}">{escape(region)}</span></td>
          <td>{escape(o.get('salary') or '—')}</td>
          <td>{_fmt(o.get('opening_date'))}</td>
          <td class="deadline">{_fmt(o.get('deadline'))}</td>
          <td><span class="pill pill-src">{escape(source)}</span></td>
          <td>{' '.join(badges)}</td>
        </tr>""")

    body = "\n".join(rows) if rows else (
        '<tr><td colspan="8" class="empty">No opportunities yet. '
        'Run a scan or wait for the next scheduled one.</td></tr>'
    )

    by_source = "".join(
        f'<div class="stat"><b>{v}</b><span>{SOURCE_LABELS.get(k, k)}</span></div>'
        for k, v in sorted(stats.get("by_source", {}).items())
    ) or '<div class="stat"><b>0</b><span>sources</span></div>'

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Apprenticeship Watcher — North West</title>
<style>
  :root {{ --bg:#0b1220; --card:#111a2c; --border:#1e2a44; --text:#e6edf7;
          --muted:#8fa3c0; --accent:#1168ea; --green:#22c55e; --amber:#f59e0b;
          --red:#ef4444; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:Inter,-apple-system,Segoe UI,Roboto,sans-serif;
         background:var(--bg); color:var(--text); }}
  header {{ padding:22px 28px; border-bottom:1px solid var(--border);
           display:flex; align-items:center; justify-content:space-between;
           flex-wrap:wrap; gap:12px; }}
  h1 {{ font-size:20px; margin:0; }}
  h1 small {{ color:var(--muted); font-weight:400; font-size:13px; }}
  .stats {{ display:flex; gap:14px; }}
  .stat {{ background:var(--card); border:1px solid var(--border);
          border-radius:10px; padding:8px 14px; text-align:center; }}
  .stat b {{ display:block; font-size:20px; color:var(--accent); }}
  .stat span {{ font-size:11px; color:var(--muted); }}
  .filters {{ padding:14px 28px; display:flex; gap:10px; flex-wrap:wrap;
             align-items:center; }}
  .filters select, .filters input {{
      background:var(--card); color:var(--text); border:1px solid var(--border);
      border-radius:8px; padding:8px 10px; font-size:13px; }}
  .filters label {{ color:var(--muted); font-size:12px; }}
  .wrap {{ padding:0 28px 40px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ text-align:left; color:var(--muted); font-weight:600; font-size:11px;
        text-transform:uppercase; letter-spacing:.04em; padding:10px 8px;
        border-bottom:1px solid var(--border); }}
  td {{ padding:12px 8px; border-bottom:1px solid var(--border);
        vertical-align:top; }}
  .role a {{ color:var(--text); text-decoration:none; font-weight:600; }}
  .role a:hover {{ color:var(--accent); }}
  .sub {{ color:var(--muted); font-size:12px; margin-top:2px; }}
  .deadline {{ white-space:nowrap; }}
  .badge {{ font-size:10px; font-weight:700; padding:3px 7px; border-radius:6px;
            margin-right:4px; white-space:nowrap; }}
  .badge-new {{ background:rgba(34,197,94,.15); color:var(--green); }}
  .badge-close {{ background:rgba(245,158,11,.15); color:var(--amber); }}
  .badge-closed {{ background:rgba(239,68,68,.15); color:var(--red); }}
  .pill {{ font-size:11px; padding:3px 8px; border-radius:20px;
          background:var(--card); border:1px solid var(--border);
          color:var(--muted); white-space:nowrap; }}
  .pill-manchester {{ color:#7dd3fc; border-color:#0e7490; }}
  .pill-leeds {{ color:#c4b5fd; border-color:#6d28d9; }}
  .pill-liverpool {{ color:#fca5a5; border-color:#b91c1c; }}
  .pill-sheffield {{ color:#86efac; border-color:#15803d; }}
  .pill-nw {{ color:#fcd34d; border-color:#a16207; }}
  .pill-src {{ color:var(--muted); }}
  .row-closed {{ opacity:.45; }}
  .row-closed .role a {{ text-decoration:line-through; }}
  .empty {{ text-align:center; color:var(--muted); padding:40px; }}
  .foot {{ padding:16px 28px; color:var(--muted); font-size:12px;
           border-top:1px solid var(--border); }}
  .btn {{ background:var(--accent); color:#fff; border:none; border-radius:8px;
         padding:8px 14px; font-size:13px; cursor:pointer; }}
  .btn:hover {{ filter:brightness(1.1); }}
</style></head><body>
<header>
  <h1>Apprenticeship Watcher <small>North West England · Manchester &amp; Leeds</small></h1>
  <div class="stats">
    <div class="stat"><b>{stats.get('active', 0)}</b><span>active</span></div>
    <div class="stat"><b>{stats.get('with_deadline', 0)}</b><span>with deadline</span></div>
    {by_source}
  </div>
</header>
<div class="filters">
  <label>Region
    <select id="f-region" onchange="apply()">
      <option value="">All</option>
      <option value="manchester">Manchester</option>
      <option value="leeds">Leeds</option>
      <option value="liverpool">Liverpool</option>
      <option value="sheffield">Sheffield</option>
      <option value="nw">North West</option>
      <option value="other">Other</option>
    </select>
  </label>
  <label>Source
    <select id="f-source" onchange="apply()">
      <option value="">All</option>
      <option value="govuk">GOV.UK</option>
      <option value="employer">Employer</option>
      <option value="linkedin">LinkedIn</option>
    </select>
  </label>
  <label>Status
    <select id="f-status" onchange="apply()">
      <option value="active">Active</option>
      <option value="all">All</option>
      <option value="closed">Closed</option>
    </select>
  </label>
  <label><input type="checkbox" id="f-close" onchange="apply()"> Closing soon</label>
  <label>Search <input type="text" id="f-q" placeholder="role, employer…"
         oninput="apply()"></label>
  <button class="btn" onclick="runScan()">Run scan now</button>
</div>
<div class="wrap">
  <table>
    <thead><tr>
      <th>Role</th><th>Location</th><th>Region</th><th>Salary</th>
      <th>Opened</th><th>Deadline</th><th>Source</th><th>Flags</th>
    </tr></thead>
    <tbody id="rows">{body}</tbody>
  </table>
</div>
<div class="foot">Scans every {config.scan_interval_minutes} min · alerts via WhatsApp ·
  <a href="/api/opportunities" style="color:var(--accent)">JSON API</a></div>
<script>
  const rows = Array.from(document.querySelectorAll('#rows tr'));
  function apply() {{
    const region = document.getElementById('f-region').value;
    const source = document.getElementById('f-source').value;
    const status = document.getElementById('f-status').value;
    const close = document.getElementById('f-close').checked;
    const q = document.getElementById('f-q').value.toLowerCase();
    rows.forEach(r => {{
      const t = r.textContent.toLowerCase();
      const regionCell = r.querySelector('.pill').textContent.toLowerCase();
      const srcCell = r.querySelector('.pill-src').textContent.toLowerCase();
      const isClosed = r.classList.contains('row-closed');
      const closing = r.textContent.includes('CLOSES');
      let show = true;
      if (region && regionCell !== region) show = false;
      if (source && srcCell !== source) show = false;
      if (status === 'active' && isClosed) show = false;
      if (status === 'closed' && !isClosed) show = false;
      if (close && !closing) show = false;
      if (q && !t.includes(q)) show = false;
      r.style.display = show ? '' : 'none';
    }});
  }}
  async function runScan() {{
    const b = document.querySelector('.btn');
    b.textContent = 'Scanning…'; b.disabled = true;
    await fetch('/api/run');
    location.reload();
  }}
</script>
</body></html>"""
