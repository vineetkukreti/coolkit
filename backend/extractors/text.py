"""Pure text extraction functions — no external dependencies beyond re."""

import re

from config import DOMAIN_KEYWORDS, ROLE_KEYWORDS

EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')


def extract_emails(text: str) -> str:
    """Return comma-separated emails found in text, or empty string."""
    found = EMAIL_RE.findall(text)
    seen = set()
    unique = []
    for e in found:
        if e.lower() not in seen:
            seen.add(e.lower())
            unique.append(e)
    return ", ".join(unique)


def extract_roles(text: str) -> str:
    """Return comma-separated roles detected in text via keyword matching."""
    lower = text.lower()
    found = []
    for role, keywords in ROLE_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            found.append(role)
    return ", ".join(found) if found else "Not specified"


def extract_location(text: str) -> str:
    """Detect common location mentions in post content."""
    patterns = [
        r'\b(remote|work from home|wfh)\b',
        r'\b(india|bangalore|bengaluru|mumbai|delhi|hyderabad|pune|chennai|kolkata|noida|gurgaon)\b',
        r'\b(usa|united states|new york|san francisco|boston|seattle|chicago|los angeles)\b',
        r'\b(uk|london|manchester|edinburgh)\b',
        r'\b(canada|toronto|vancouver|montreal)\b',
        r'\b(hybrid|on.?site|in.?office)\b',
    ]
    found = []
    lower = text.lower()
    for pattern in patterns:
        matches = re.findall(pattern, lower, re.IGNORECASE)
        found.extend(matches)

    seen = set()
    result = []
    for m in found:
        key = m.lower()
        if key not in seen:
            seen.add(key)
            result.append(m.title())
    return ", ".join(result) if result else ""


def normalize_experience(raw: str) -> str:
    """Normalize experience to clean format: '2 years', '3-5 years', etc."""
    if not raw:
        return ""
    raw = raw.lower().strip()

    if any(kw in raw for kw in ["fresher", "entry", "junior", "0 year", "no experience"]):
        return "0 years (Fresher)"

    m = re.search(r'(\d+)\s*(?:to|-)\s*(\d+)', raw)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        return f"{lo}-{hi} years"

    m = re.search(r'(\d+)\+?', raw)
    if m:
        n = int(m.group(1))
        suffix = "year" if n == 1 else "years"
        plus = "+" if "+" in raw else ""
        return f"{n}{plus} {suffix}"

    return raw


def extract_experience(text: str) -> str:
    """Extract experience requirements like '3+ years', '2-5 years'."""
    patterns = [
        r'(\d+\+?\s*(?:to|-)\s*\d*\+?\s*years?\s+(?:of\s+)?experience)',
        r'(\d+\+?\s*years?\s+(?:of\s+)?experience)',
        r'(experience[:\s]+\d+\+?\s*(?:to|-)\s*\d*\+?\s*years?)',
        r'(freshers?\s+welcome|entry.?level)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return normalize_experience(m.group(1).strip())
    return ""


def score_domain_relevance(text: str) -> str:
    """Score how relevant a post is to healthcare/medical/clinical domain."""
    lower = text.lower()
    matches = sum(1 for kw in DOMAIN_KEYWORDS if kw in lower)
    if matches >= 3:
        return "High"
    elif matches >= 1:
        return "Medium"
    return "Low"


def is_hiring_post(text: str) -> bool:
    """Quick check if a post is actually about hiring."""
    hiring_signals = [
        "we are hiring", "we're hiring", "now hiring", "job opening",
        "open position", "looking for", "join our team", "join us",
        "send your resume", "send resume", "send cv", "apply now",
        "dm me", "direct message", "reach out", "email us", "email at",
        "@gmail", "@yahoo", "@outlook", "careers@", "hr@", "jobs@",
        "talent@", "recruiting", "recruiter", "opportunity",
    ]
    lower = text.lower()
    return any(signal in lower for signal in hiring_signals)
