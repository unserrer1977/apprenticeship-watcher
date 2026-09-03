"""GOV.UK Find an apprenticeship source (primary).

Scrapes the public, server-rendered search page. Reliable and official, with
closing dates, wages, employers and locations.
"""
import logging
import re
from datetime import datetime
from typing import Iterator, Optional

import requests
from bs4 import BeautifulSoup

from ..config import config
from ..models import Opportunity
from .base import Source
from .region import normalize_location, tag_region

log = logging.getLogger(__name__)

BASE = "https://www.findapprenticeship.service.gov.uk"
SEARCH_URL = BASE + "/apprenticeships"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}

_DATE_FORMATS = ["%A %d %B %Y", "%d %B %Y", "%A %d %b %Y", "%d %b %Y"]


def _parse_date(text: str) -> Optional[str]:
    """Parse a human date like 'Wednesday 30 September 2026' to ISO."""
    if not text:
        return None
    text = text.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


class GovUKSource(Source):
    name = "govuk"

    def fetch(self) -> Iterator[Opportunity]:
        # 1. Location-based searches (the standard NW coverage).
        for location in config.locations:
            for page in range(1, config.govuk_pages + 1):
                try:
                    items = self._fetch_page(location, page)
                except requests.RequestException as exc:
                    log.warning("govuk page %d (%s) failed: %s",
                                page, location, exc)
                    break
                if not items:
                    break
                for opp in items:
                    yield opp
        # 2. Big-employer name searches (national — catches the firms that
        #    recruit through the portal regardless of NW location).
        if getattr(config, "employer_search_enabled", False):
            for employer in config.employer_search_terms:
                try:
                    items = self._search_employer(employer, page=1)
                except requests.RequestException as exc:
                    log.warning("govuk employer search (%s) failed: %s",
                                employer, exc)
                    continue
                for opp in items:
                    yield opp

    def _search_employer(self, employer: str, page: int) -> list:
        params = {
            "searchTerm": employer,
            "sort": "AgeAsc",  # newest first
            "pageNumber": page,
        }
        resp = requests.get(SEARCH_URL, params=params, headers=HEADERS,
                            timeout=30)
        resp.raise_for_status()
        # National search — no location, so region derives from the result.
        return self._parse(resp.text, "")

    def _fetch_page(self, location: str, page: int) -> list:
        params = {
            "location": location,
            "distance": config.distance,
            "searchTerm": "",
            "sort": "AgeAsc",  # newest first
            "pageNumber": page,
        }
        resp = requests.get(SEARCH_URL, params=params, headers=HEADERS,
                            timeout=30)
        resp.raise_for_status()
        return self._parse(resp.text, location)

    def _parse(self, html: str, query_location: str) -> list:
        soup = BeautifulSoup(html, "html.parser")
        out = []
        for li in soup.select("li.das-search-results__list-item"):
            opp = self._parse_item(li, query_location)
            if opp:
                out.append(opp)
        return out

    def _parse_item(self, li, query_location: str) -> Optional[Opportunity]:
        title_el = li.select_one("span[id$='-vacancy-title']")
        link_el = li.select_one("a.das-search-results__link")
        if not title_el or not link_el:
            return None
        role = title_el.get_text(strip=True)
        link = link_el.get("href", "")
        if link.startswith("/"):
            link = BASE + link

        employer = ""
        location = ""
        start_date = ""
        training_course = ""
        salary = ""
        closing_text = ""
        posted_text = ""

        for p in li.select("p"):
            text = p.get_text(" ", strip=True)
            b = p.find("b")
            label = b.get_text(strip=True) if b else ""
            classes = p.get("class", [])
            has_mb0 = "govuk-!-margin-bottom-0" in classes
            has_grey = "das-!-color-dark-grey" in classes
            if label == "Start date":
                start_date = text.replace("Start date", "").strip()
            elif label == "Training course":
                training_course = text.replace("Training course", "").strip()
            elif label == "Wage":
                salary = text.replace("Wage", "").strip()
            elif has_grey and not has_mb0 and not location:
                # Location paragraph (the posted-date footer also has the grey
                # class but additionally has margin-bottom-0).
                location = text
            elif "Closes in" in text:
                closing_text = text
            elif "Posted" in text and not posted_text:
                posted_text = text
            elif has_mb0 and not has_grey and not employer:
                employer = text

        # Closing date: "Closes in 28 days (Wednesday 30 September 2026)"
        deadline = None
        m = re.search(r"\(([^)]+)\)", closing_text)
        if m:
            deadline = _parse_date(m.group(1))

        # Posted date: "Posted 17 July 2026"
        opening_date = None
        m = re.search(r"Posted\s+(.+)", posted_text)
        if m:
            opening_date = _parse_date(m.group(1))

        loc_clean = normalize_location(location)
        region = tag_region(location or query_location)

        return Opportunity(
            source=self.name,
            employer=employer,
            role=role,
            location=loc_clean or query_location,
            salary=salary,
            application_link=link,
            opening_date=opening_date or "",
            deadline=deadline or "",
            start_date=start_date,
            training_course=training_course,
            region=region,
        )
