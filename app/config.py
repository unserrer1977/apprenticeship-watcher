"""Configuration loaded from environment variables."""
import json
import os


def _bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _list(name: str, default: str) -> list:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        return [x.strip() for x in default.split(",") if x.strip()]
    return [x.strip() for x in v.split(",") if x.strip()]


class Config:
    def __init__(self):
        self.port = _int("PORT", 8080)
        self.data_dir = os.getenv("DATA_DIR", "/data")
        self.db_path = os.getenv("DB_PATH", os.path.join(self.data_dir, "watcher.db"))

        # Monitoring
        self.locations = _list(
            "LOCATIONS",
            "Manchester,Leeds,Liverpool,Sheffield,Bradford,Preston,"
            "Warrington,Bolton,Salford,Huddersfield",
        )
        self.distance = _int("DISTANCE", 15)
        self.scan_interval_minutes = _int("SCAN_INTERVAL_MINUTES", 30)
        self.govuk_pages = _int("GOVUK_PAGES", 3)

        # Alerts
        self.alert_enabled = _bool("ALERT_ENABLED", True)
        self.deadline_alert_days = _int("DEADLINE_ALERT_DAYS", 7)
        self.whatsapp_base_url = os.getenv("WHATSAPP_BASE_URL", "").strip()
        self.whatsapp_api_key = os.getenv("WHATSAPP_API_KEY", "").strip()
        self.whatsapp_phone = os.getenv("WHATSAPP_PHONE", "").strip()

        # Optional sources
        self.li_at = os.getenv("LI_AT", "").strip()
        self.employer_pages = self._json_list("EMPLOYER_PAGES", [])

        # NOTE: the gov.uk searchTerm field is a relevance search, not an exact
        # employer filter — searching "EY"/"Arm"/"Sky" matches Early Years /
        # pub arms / skyline, flooding the DB with noise. Big-firm coverage is
        # handled properly by the Higherin source, so this is OFF by default.
        self.employer_search_terms = self._json_list("EMPLOYER_SEARCH_TERMS", [])
        self.employer_search_enabled = _bool("EMPLOYER_SEARCH_ENABLED", False)

        # Higherin (RateMyApprenticeship) — the authoritative source for
        # big-firm and degree apprenticeships.
        self.higherin_routes = self._json_list(
            "HIGHERIN_ROUTES", ["degree-apprenticeship", "apprenticeships"]
        )
        self.higherin_enabled = _bool("HIGHERIN_ENABLED", True)

        # Scope: only track apprenticeships from major employers. When true
        # (default), any role whose employer isn't in the major list is dropped.
        self.only_major_firms = _bool("ONLY_MAJOR_FIRMS", True)

    @staticmethod
    def _json_list(name: str, default):
        v = os.getenv(name)
        if not v or not v.strip():
            return default
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        return default

    @property
    def alerts_configured(self) -> bool:
        return (
            self.alert_enabled
            and bool(self.whatsapp_base_url)
            and bool(self.whatsapp_phone)
        )


config = Config()