"""LinkedIn source (optional).

LinkedIn's job search is heavily JS-gated and requires an authenticated
session. This source uses a `LI_AT` session cookie from the LI_AT env var. If
no cookie is configured it yields nothing (and is skipped). Even with a cookie,
LinkedIn may still block server-side requests; this is best-effort.
"""
import logging
from typing import Iterator

import requests
from bs4 import BeautifulSoup

from ..config import config
from ..models import Opportunity
from .base import Source
from .region import tag_region

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    )
}


class LinkedInSource(Source):
    name = "linkedin"

    def fetch(self) -> Iterator[Opportunity]:
        if not config.li_at:
            log.info("LinkedIn source skipped (no LI_AT cookie configured)")
            return
        cookies = {"li_at": config.li_at}
        for location in config.locations[:2]:  # Manchester + Leeds
            url = (
                "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/"
                f"search?keywords=apprenticeship&location={location}"
                "&f_TPR=r2592000"
            )
            try:
                resp = requests.get(url, headers=HEADERS, cookies=cookies,
                                    timeout=30)
                if resp.status_code != 200:
                    log.warning("LinkedIn returned %s for %s",
                                resp.status_code, location)
                    continue
                for opp in self._parse(resp.text, location):
                    yield opp
            except requests.RequestException as exc:
                log.warning("LinkedIn %s failed: %s", location, exc)

    def _parse(self, html: str, location: str) -> Iterator[Opportunity]:
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select("li, .job-search-card, .base-card"):
            title_el = card.select_one(".base-search-card__title, h3")
            link_el = card.select_one("a.base-card__full-link, a[href*='/jobs/view']")
            company_el = card.select_one(".base-search-card__subtitle, h4")
            if not title_el or not link_el:
                continue
            role = title_el.get_text(strip=True)
            link = link_el.get("href", "")
            company = company_el.get_text(strip=True) if company_el else ""
            yield Opportunity(
                source=self.name,
                employer=company,
                role=role,
                location=location,
                application_link=link,
                region=tag_region(location),
            )
