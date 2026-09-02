"""Source crawlers. Each Source subclass yields Opportunity objects."""
from .base import Source
from .govuk import GovUKSource
from .employer_pages import EmployerPagesSource
from .linkedin import LinkedInSource

__all__ = [
    "Source",
    "GovUKSource",
    "EmployerPagesSource",
    "LinkedInSource",
]
