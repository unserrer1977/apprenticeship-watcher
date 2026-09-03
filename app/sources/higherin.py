"""Higherin (formerly RateMyApprenticeship) source.

Higherin is the UK's leading aggregator of employer apprenticeships and is how
the big firms (KPMG, Deloitte, PwC, EY, UBS, Unilever, ...) advertise their
degree apprenticeships. It embeds its live search results as JSON in the page
(`window.__RMP_SEARCH_RESULTS_INITIAL_STATE__`), which we parse.

Rows carry employer, role, locations, salary, a real application deadline and
a direct apply URL — everything the watcher needs.
"""
import json
import logging
import re
from datetime import datetime
from typing import Iterator, Optional

import requests

from ..config import config
from ..models import Opportunity
from ..scoring import is_major_employer
from .base import Source
from .region import tag_region

log = logging.getLogger(__name__)

BASE = "https://higherin.com"
STATE_RE = re.compile(
    r"window\.__RMP_SEARCH_RESULTS_INITIAL_STATE__\s*=\s*(\{.*?\});\s*</script>",
    re.S,
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}

# Default routes. The degree-apprenticeship route is the priority; the broader
# apprenticeships route is also crawled but only high-signal rows are kept.
# Override via HIGHERIN_ROUTES (JSON array of route suffixes).
DEFAULT_ROUTES = ["degree-apprenticeship", "apprenticeships"]


def _parse_deadline(text) -> Optional[str]:
    """Parse '25th January 2027' -> '2027-01-25'. Returns None if not a date."""
    if not text:
        return None
    t = text.strip()
    if t.lower() in ("ongoing", "none", "", "rolling", "apply now"):
        return None
    # Strip English ordinals: 1st, 2nd, 3rd, 4th ...
    t = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", t)
    for fmt in ("%d %B %Y", "%d %b %Y", "%d %B %y"):
        try:
            return datetime.strptime(t, fmt).date().isoformat()
        except ValueError:
            continue
    # Also try "January 25, 2027" style.
    try:
        return datetime.strptime(t, "%B %d, %Y").date().isoformat()
    except ValueError:
        pass
    return None  # unparseable deadline -> treat as unknown


class HigherinSource(Source):
    name = "higherin"

    def fetch(self) -> Iterator[Opportunity]:
        routes = getattr(config, "higherin_routes", None) or DEFAULT_ROUTES
        for route in routes:
            try:
                for opp in self._iter_route(route):
                    yield opp
            except requests.RequestException as exc:
                log.warning("higherin route %s failed: %s", route, exc)
            except json.JSONDecodeError as exc:
                log.warning("higherin route %s: bad state JSON: %s", route, exc)

    def _iter_route(self, route: str) -> Iterator[Opportunity]:
        page = 1
        total = None
        while True:
            url = f"{BASE}/search-jobs/{route}"
            if page > 1:
                url += f"?page={page}"
            resp = requests.get(url, headers=HEADERS, timeout=45)
            resp.raise_for_status()
            state = self._extract_state(resp.text)
            if state is None:
                log.warning("higherin route %s page %d: no embedded state",
                            route, page)
                return
            if total is None:
                total = state.get("meta", {}).get("totalResults") or 0
            rows = state.get("data", [])
            if not rows:
                return
            for row in rows:
                opp = self._row_to_opp(row)
                if opp and self._keep(opp):
                    yield opp
            # Pagination: stop when we've covered total or a short page.
            if total and page * 20 >= total:
                return
            if len(rows) < 20:
                return
            page += 1

    @staticmethod
    def _extract_state(html: str) -> Optional[dict]:
        m = STATE_RE.search(html)
        if not m:
            # Fallback: slice between the marker and </script>.
            i = html.find("window.__RMP_SEARCH_RESULTS_INITIAL_STATE__")
            if i == -1:
                return None
            seg = html[i:html.find("</script>", i)]
            seg = seg[seg.find("=") + 1:].strip()
        else:
            seg = m.group(1)
        try:
            return json.loads(seg)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _row_to_opp(row: dict) -> Optional[Opportunity]:
        if not row.get("jobTitle"):
            return None
        company = row.get("companyName") or ""
        locations = row.get("jobLocationNames") or []
        loc_str = ", ".join(locations) if locations else ""
        salary = row.get("salary") or row.get("salaryNotes") or ""
        return Opportunity(
            source="higherin",
            employer=company,
            role=row["jobTitle"],
            location=loc_str,
            salary=salary,
            application_link=row.get("url") or "",
            deadline=_parse_deadline(row.get("deadline")) or "",
            start_date=row.get("employmentStartDate") or "",
            region=tag_region(loc_str),
        )

    @staticmethod
    def _keep(opp: Opportunity) -> bool:
        """Keep a row.

        Degree-apprenticeship roles are all high-value and kept. For the broad
        apprenticeships route, only keep roles from major employers or in the
        watcher's target topics (avoiding QA/Arsenal-style noise).
        """
        if "degree" in opp.role.lower() or "degree" in opp.training_course.lower():
            return True
        if is_major_employer(opp.employer):
            return True
        from ..scoring import classify_topic
        return bool(classify_topic(opp.role, opp.training_course))