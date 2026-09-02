"""Base class for all opportunity sources."""
import hashlib
import logging
from typing import Iterator, List

from ..models import Opportunity

log = logging.getLogger(__name__)


class Source:
    name = "base"

    def fetch(self) -> Iterator[Opportunity]:
        """Yield Opportunity objects. Subclasses implement this."""
        raise NotImplementedError

    @staticmethod
    def make_dedup_key(source: str, employer: str, role: str,
                       location: str, link: str) -> str:
        raw = "|".join(
            [source, (employer or "").strip().lower(),
             (role or "").strip().lower(),
             (location or "").strip().lower(), (link or "").strip()]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def run(self) -> List[Opportunity]:
        """Fetch all opportunities from this source."""
        out = []
        try:
            for opp in self.fetch():
                if not opp.role or not opp.application_link:
                    continue
                if not opp.dedup_key:
                    opp.dedup_key = self.make_dedup_key(
                        opp.source, opp.employer, opp.role,
                        opp.location, opp.application_link,
                    )
                out.append(opp)
        except Exception as exc:  # noqa: BLE001 - a source must never kill a scan
            log.warning("Source %s failed: %s", self.name, exc)
        log.info("Source %s yielded %d opportunities", self.name, len(out))
        return out
