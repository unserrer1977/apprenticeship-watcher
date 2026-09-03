"""Priority scoring for apprenticeship opportunities.

Each opportunity is scored 0-100 for how well it matches the watcher's focus:
digital marketing / AI / business topics, degree apprenticeships (level 6-7),
and hiring by major employers (KPMG, Deloitte, PwC, EY, ...).

Scores are stored on the row at upsert time so the dashboard and alerts can
rank and spotlight the best matches without recomputing on every read.
"""
import re
from typing import List, Tuple

# ─── Target topics ─────────────────────────────────────────────────────────
# Each topic is a list of keywords matched (case-insensitively) against the
# role title, training course and description. Order lists most-specific-first.
DIGITAL_MARKETING: List[str] = [
    "digital market", "digital market", "social media", "content creator",
    "paid media", "seo", "ppc", "email market", "growth market", "digital",
    "marketing", "content", "advertis", "brand", "ecommerce", "e-commerce",
    "crm", "campaign", "creative media", "media", "public relations", "pr ",
    "copywriting", "web design", "ux", "insights", "audience",
]
AI: List[str] = [
    "artificial intelligence", "machine learning", "data science",
    "data scientist", "ai ", "ai&", "computer vision", "llm", "nlp",
    "data analyst", "data engineering", "data engineer", "cloud engineer",
    "cloud analyst", "data",
]
BUSINESS: List[str] = [
    "digital market", "business analyst", "project management",
    "project manager", "business admin", "business administration",
    "management", "finance", "accounting", "accountant", "consult",
    "commercial", "operations", "strategy", "people", "hr consultant",
    "human resources", "risk", "audit", "tax", "insurance", "procurement",
    "supply chain", "sales", "business", "administration", "operations mgmt",
    "legal", "law ", "customer service", "team leader", "supervisor",
]

TOPIC_LABELS = {
    "digital_marketing": "Digital Marketing",
    "ai": "AI & Data",
    "business": "Business",
}

# ─── Major employers (weighted heavily) ────────────────────────────────────
_MAJOR_EMPLOYERS: List[str] = [
    "kpmg", "deloitte", "pwc", "ernst & young", "ey", "accenture",
    "mckinsey", "bain &", "bcg", "boston consulting", "goldman",
    "jpmorgan", "jp morgan", "j.p. morgan", "morgan stanley", "barclays",
    "hsbc", "lloyds", "natwest", "royal bank of scotland", "santander",
    "nats", "bae systems", "rolls-royce", "rolls royce", "siemens", "ibm",
    "microsoft", "amazon", "google", "meta", "apple", "cisco", "bt group",
    "bt", "vodafone", "sky", "bbc", "itv", "unilever", "p&g",
    "procter & gamble", "gsk", "glaxosmithkline", "astrazeneca", "bp",
    "shell", "centrica", "national grid", "sse", "capita", "serco",
    "dyson", "arm holdings", "johnson & johnson", "nutanix", "nvidia",
]

# Match keywords as whole words/phrases (case-insensitive). "ey", "bt", "bp",
# "sky", "sse" are short but rare enough as standalone employer tokens.
_COMPILED_MAJOR = [
    re.compile(r"\b" + re.escape(k) + r"\b", re.I) for k in _MAJOR_EMPLOYERS
]

# Degree apprenticeships are level 6 or 7 (or explicitly "degree").
_DEGREE_RE = re.compile(
    r"\(?(level\s*[67]|degree|honours|bachelor|masters|postgraduate)\)?",
    re.I,
)

# gov.uk levels present in the "Training course" field, e.g. "(level 4)".
_LEVEL_RE = re.compile(r"\(level\s*(\d)\)", re.I)


def _match_any(text: str, keywords: List[str]) -> bool:
    if not text:
        return False
    for kw in keywords:
        # Short keywords may over-match; still acceptable for scoring.
        if kw in text:
            return True
    return False


def classify_topic(role: str, training_course: str, description: str = "") -> str:
    """Return the best-matching target topic, or '' if none."""
    candidate = f"{role} {training_course} {description}".lower()
    # Normalise "ai" and "pr" collisions by checking for word-ish presence.
    if _match_any(candidate, AI):
        return "ai"
    if _match_any(candidate, DIGITAL_MARKETING):
        return "digital_marketing"
    if _match_any(candidate, BUSINESS):
        return "business"
    return ""


def is_degree_apprenticeship(role: str, training_course: str) -> bool:
    """True for level 6/7 (degree-level) apprenticeships."""
    txt = f"{role} {training_course}"
    if _DEGREE_RE.search(txt):
        return True
    m = _LEVEL_RE.search(training_course or "")
    if m and int(m.group(1)) >= 6:
        return True
    return False


def is_major_employer(employer: str) -> bool:
    if not employer:
        return False
    low = employer.lower().strip()
    for pat in _COMPILED_MAJOR:
        if pat.search(low):
            return True
    return False


def score_opportunity(role: str, training_course: str, employer: str,
                      description: str = "") -> dict:
    """Return a score dict for one opportunity.

    Returns: {priority (int 0-100), topic, is_degree, big_employer}
    """
    topic = classify_topic(role, training_course, description)
    degree = is_degree_apprenticeship(role, training_course)
    big = is_major_employer(employer)

    score = 10  # baseline for any tracked role
    if topic in ("digital_marketing", "ai"):
        score += 40  # the watcher's primary focus
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
