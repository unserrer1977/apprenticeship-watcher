"""Best-effort crawler for employer career pages.

Configure a list of career-page URLs via the EMPLOYER_PAGES env var (JSON).
For each page it extracts links that look like job/apprenticeship postings.
This is inherently fragile (career pages vary), so it degrades gracefully and
never breaks a scan.
"""
import logging
import re
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

# Keywords that mark a link as a job/apprenticeship posting.
_JOB_HREF = re.compile(
    r"(job|vacanc|career|apprentice|position|role|opening)", re.I
)
_JOB_TEXT = re.compile(
    r"(apprentice|job|vacanc|graduate|trainee|position|role)", re.I
)


class EmployerPagesSource(Source):
    name = "employer"

    def fetch(self) -> Iterator[Opportunity]:
        for entry in config.employer_pages:
            url = entry if isinstance(entry, str) else entry.get("url", "")
            if not url:
                continue
            try:
                for opp in self._crawl(url):
                    yield opp
            except requests.RequestException as exc:
                log.warning("employer page %s failed: %s", url, exc)

    def _crawl(self, url: str) -> Iterator[Opportunity]:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(" ", strip=True)
            if not text or len(text) < 4:
                continue
            if not (_JOB_HREF.search(href) or _JOB_TEXT.search(text)):
                continue
            link = href if href.startswith("http") else _abs(url, href)
            if link in seen:
                continue
            seen.add(link)
            # Skip obvious nav/footer links.
            if any(k in text.lower() for k in
                   ("home", "about us", "contact", "login", "sign in",
                    "cookie", "privacy", "terms", "search", "apply now",
                    "register")):
                continue
            yield Opportunity(
                source=self.name,
                employer=_employer_from_url(url),
                role=text[:200],
                location="",
                application_link=link,
                region=tag_region(""),
            )


def _abs(base: str, href: str) -> str:
    from urllib.parse import urljoin
    return urljoin(base, href)


def _employer_from_url(url: str) -> str:
    from urllib.parse import urlparse
    host = urlparse(url).netloc
    host = host.replace("www.", "").replace("careers.", "").replace("jobs.", "")
    parts = host.split(".")
    return parts[0].title() if parts else host
