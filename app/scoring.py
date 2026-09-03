"""Priority scoring prioritizes opportunities.

Each opportunity is scored 0-100 for how well it matches the watcher's focus:
digital marketing / AI / business topics, degree apprenticeships (level 6-7),
and hiring by major employers (KPMG, Deloitte, PwC, EY, ...).

When ONLY_MAJOR_FIRMS is enabled, only opportunities whose employer matches the
major-employer allowlist are stored at all.
"""
import re
from typing import List

DIGITAL_MARKETING: List[str] = [
    "digital market", "social media", "content creator", "paid media", "seo",
    "ppc", "email market", "growth market", "digital", "marketing", "content",
    "advertis", "brand", "ecommerce", "e-commerce", "crm", "campaign",
    "creative media", "media", "public relations", "copywriting", "web design",
    "ux", "insights", "audience",
]
AI: List[str] = [
    "artificial intelligence", "machine learning", "data science",
    "data scientist", "computer vision", "llm", "nlp", "data analyst",
    "data engineering", "data engineer", "cloud engineer", "cloud analyst",
    "data",
]
BUSINESS: List[str] = [
    "digital market", "business analyst", "project management",
    "project manager", "business admin", "business administration",
    "management", "finance", "accounting", "accountant", "consult",
    "commercial", "operations", "strategy", "people", "hr consultant",
    "human resources", "risk", "audit", "tax", "insurance", "procurement",
    "supply chain", "sales", "business", "administration", "legal", "law",
    "customer service", "team leader", "supervisor",
]

TOPIC_LABELS = {
    "digital_marketing": "Digital Marketing",
    "ai": "AI & Data",
    "business": "Business",
}

# ── Major employers (the ONLY_MAJOR_FIRMS allowlist) ───────────────────────
# Distinctive, unambiguous names — matched anywhere as whole words.
_MAJOR_EMPLOYERS: List[str] = [
    # Big 4 & professional services
    "kpmg", "deloitte", "pwc", "ernst & young", "accenture", "mckinsey",
    "boston consulting", "bcg", "capgemini", "grant thornton", "mazars",
    "eversheds", "clifford chance", "linklaters", "dla piper", "ashurst",
    "savills", "bdo",
    # Investment banks & big finance
    "goldman", "jpmorgan", "jp morgan", "j.p. morgan", "morgan stanley",
    "barclays", "hsbc", "natwest", "royal bank of scotland", "santander", "lloyds",
    "deutsche bank", "nomura", "blackrock",
    # Tech
    "microsoft", "amazon", "google", "meta", "apple", "cisco", "ibm",
    "oracle", "salesforce", "sap", "nvidia", "intel", "arm holdings",
    "nutanix", "epam",
    # Telecom / broadcast / media
    "vodafone", "channel 4", "virgin media", "itv",
    # Energy / utilities
    "centrica", "national grid", "schneider electric", "wessex water",
    "network rail", "e.on",
    # Aerospace / engineering / auto
    "bae systems", "rolls-royce", "rolls royce", "jaguar land rover",
    "ge aviation", "ge aerospace", "volkswagen", "honeywell", "galliford try",
    "laing o'rourke", "transport for london", "babcock", "thales", "bosch",
    "airbus", "siemens",
    # Consumer / pharma / FMCG
    "procter & gamble", "glaxosmithkline", "johnson & johnson", "coca-cola",
    "reckitt", "astrazeneca", "pepsico", "arcadis", "beazley",
    "unilever", "nestle", "mars", "loreal", "shell", "bmw", "nissan", "dyson",
    # Broad services
    "balfour beatty", "capita", "serco", "mitie", "dwp", "vistra",
    "gkn", "cummins", "wates", "kier",
]

# Short tokens (≤4 chars) that are common words — matched only when the employer
# string STARTS with them, so "Sky"/"BT"/"EY"/"BP"/"EDF"/"GB" match but
# "Blue Sky Dental"/"High Sky" do not.
_SHORT_TOKENS: List[str] = [
    "bt", "bp", "edf", "ge", "bbc", "ey", "ubs", "sse", "nats", "sky", "o2",
]

# Short token that is also a common English word; start-anchored is still used
# but the token itself is rare enough.
_COMPILED_MAJOR = [
    re.compile(r"\b" + re.escape(k) + r"\b", re.I) for k in _MAJOR_EMPLOYERS
]
_COMPILED_START = [
    re.compile(r"^" + re.escape(k) + r"\b", re.I) for k in _SHORT_TOKENS
]

# Degree apprenticeships are level 6 or 7 (or explicitly "degree").
_DEGREE_RE = re.compile(
    r"\(?(level\s*[67]|degree|honours|bachelor|masters|postgraduate)\)?",
    re.I,
)
_LEVEL_RE = re.compile(r"\(level\s*(\d)\)", re.I)


def _match_any(text: str, keywords: List[str]) -> bool:
    if not text:
        return False
    text = text.lower()
    return any(kw in text for kw in keywords)


def classify_topic(role: str, training_course: str, description: str = "") -> str:
    candidate = f"{role} {training_course} {description}".lower()
    if _match_any(candidate, AI):
        return "ai"
    if _match_any(candidate, DIGITAL_MARKETING):
        return "digital_marketing"
    if _match_any(candidate, BUSINESS):
        return "business"
    return ""


def is_degree_apprenticeship(role: str, training_course: str) -> bool:
    txt = f"{role} {training_course}"
    if _DEGREE_RE.search(txt):
        return True
    mtxt = _LEVEL_RE.search(training_course or "")
    if mtxt and int(mtxt.group(1)) >= 6:
        return True
    return False


def is_major_employer(employer: str) -> bool:
    if not employer:
        return False
    low = employer.strip().lower()
    if any(pat.search(low) for pat in _COMPILED_MAJOR):
        return True
    return any(pat.search(low) for pat in _COMPILED_START)


def score_opportunity(role: str, training_course: str, employer: str,
                      description: str = "") -> dict:
    topic = classify_topic(role, training_course, description)
    degree = is_degree_apprenticeship(role, training_course)
    big = is_major_employer(employer)
    score = 10
    if topic in ("digital_marketing", "ai"):
        score += 40
    elif topic == "business":
        score += 30
    if degree:
        score += 30
    if big:
        score += 25
    return {
        "priority": min(score, 100),
        "topic": topic,
        "is_degree": int(degree),
        "big_employer": int(big),
    }