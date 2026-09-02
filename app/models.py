"""Data model for a tracked apprenticeship opportunity."""
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Opportunity:
    id: Optional[int] = None
    source: str = ""
    employer: str = ""
    role: str = ""
    location: str = ""
    application_link: str = ""
    salary: str = ""
    opening_date: str = ""          # ISO date (posted date)
    deadline: str = ""              # ISO date (closing date)
    start_date: str = ""
    training_course: str = ""
    description: str = ""
    region: str = ""                # manchester / leeds / nw / other
    dedup_key: str = ""
    first_seen: str = ""
    last_seen: str = ""
    status: str = "active"
    alerted_new: int = 0
    alerted_deadline: int = 0

    def to_dict(self) -> dict:
        return asdict(self)
