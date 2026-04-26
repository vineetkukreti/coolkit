#!/usr/bin/env python3
"""
Shared Email Finding Strategies.

All email discovery strategies, constants, scoring, and verification
live here. Both enrich.py and cron.py import from this module.

Strategies (in priority order):
1. Hunter.io API (free tier, 25/month)
2. Website scraping (contact, about, careers pages)
3. DuckDuckGo search (via duckduckgo-search package)
4. Google search fallback
5. Person-name email patterns (firstname@, first.last@, etc.)
6. Generic email patterns (info@, hr@, careers@, etc.)
7. Domain inference from company name
"""

import os
import re
import time
import random
import logging
import socket
import smtplib
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

log = logging.getLogger("email_finder")

# ─── Shared Constants ────────────────────────────────────────────────────────

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

CONTACT_PATHS = [
    "/contact", "/contact-us", "/contactus",
    "/about", "/about-us", "/aboutus",
    "/careers", "/jobs", "/career", "/hiring", "/join-us", "/work-with-us",
    "/team", "/our-team", "/people", "/leadership",
    "/support", "/help",
    "/",
]

JUNK_DOMAINS = {
    "example.com", "test.com", "email.com", "domain.com", "yourcompany.com",
    "sentry.io", "wixpress.com", "googleapis.com", "cloudflare.com",
    "gravatar.com", "wordpress.com", "w3.org", "schema.org",
    "facebook.com", "twitter.com", "google.com", "github.com", "duckduckgo.com",
    "jquery.com", "bootstrap.com", "fontawesome.com", "tailwindcss.com",
    "linkedin.com", "instagram.com", "youtube.com", "tiktok.com",
    "apple.com", "microsoft.com", "amazon.com",
}

JUNK_PREFIXES = {"noreply", "no-reply", "donotreply", "mailer-daemon", "postmaster", "webmaster"}

# Ordered by outreach value
OUTREACH_PREFIXES = ["careers", "hr", "hiring", "jobs", "info", "contact", "hello", "team", "people", "admin"]
GENERIC_PREFIXES = ["support", "office", "business", "general"]


# ─── Shared Utilities ────────────────────────────────────────────────────────

def random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def is_junk_email(email: str) -> bool:
    """Filter obviously invalid/useless emails."""
    email = email.lower().strip()
    if len(email) < 5 or len(email) > 80:
        return True
    if "@" not in email:
        return True
    local, domain = email.rsplit("@", 1)
    if domain in JUNK_DOMAINS:
        return True
    if local in JUNK_PREFIXES:
        return True
    if any(ext in email for ext in [".png", ".jpg", ".gif", ".svg", ".css", ".js"]):
        return True
    if len(local) > 30:
        return True
    digits = sum(1 for c in local if c.isdigit())
    if len(local) > 4 and digits / len(local) > 0.6:
        return True
    return False


def score_email(email: str, verified: str = "unknown", source: str = "") -> int:
    """Score email for outreach quality.

    Args:
        verified: "accepted" (SMTP confirmed), "rejected" (SMTP rejected),
                  "unknown" (can't determine / not checked)
        source: strategy that found it (hunter_io, website, search, person_pattern, etc.)
    """
    if verified == "rejected":
        return 0

    email_lower = email.lower()
    local = email_lower.split("@")[0]
    domain = email_lower.split("@")[1] if "@" in email_lower else ""
    score = 10  # base

    # Type bonuses
    if any(local.startswith(p) for p in ["hr", "careers", "hiring", "jobs", "recruit"]):
        score += 25
    elif any(local.startswith(p) for p in ["contact", "info", "hello", "team"]):
        score += 15
    elif "." in local:  # person-name pattern (john.doe@)
        score += 20
    elif any(local.startswith(p) for p in ["admin", "office", "business"]):
        score += 5

    # Company domain > generic
    generic_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "protonmail.com"}
    if domain not in generic_domains:
        score += 10

    # Verification bonus
    if verified == "accepted":
        score += 15

    # Source trust bonus
    if source == "hunter_io":
        score += 10
    elif source == "website":
        score += 5
    elif source == "person_pattern":
        score += 5

    return score


def fetch_page(url: str, timeout: int = 10) -> str | None:
    """Fetch a page, return HTML or None."""
    try:
        resp = requests.get(url, headers=random_headers(), timeout=timeout, allow_redirects=True)
        if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
            return resp.text
    except Exception:
        pass
    return None


def extract_emails_from_html(html: str) -> set[str]:
    """Extract and deduplicate emails from HTML content."""
    soup = BeautifulSoup(html, "lxml")
    emails = set()

    # From mailto links
    for a in soup.find_all("a", href=True):
        if "mailto:" in a["href"]:
            email = a["href"].split("mailto:")[1].split("?")[0].strip().lower()
            if email and not is_junk_email(email):
                emails.add(email)

    # From text content
    text = soup.get_text(separator=" ")
    for m in EMAIL_RE.findall(text):
        m = m.lower()
        if not is_junk_email(m):
            emails.add(m)

    # From attributes (data attributes sometimes contain emails)
    for tag in soup.find_all(True):
        for attr_val in tag.attrs.values():
            if isinstance(attr_val, str):
                for m in EMAIL_RE.findall(attr_val):
                    m = m.lower()
                    if not is_junk_email(m):
                        emails.add(m)

    return emails


def extract_domain(website: str) -> str:
    """Extract clean domain from website URL."""
    if not website:
        return ""
    if not website.startswith("http"):
        website = "https://" + website
    domain = urlparse(website).netloc
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


# ─── Verification ────────────────────────────────────────────────────────────

def verify_mx(domain: str) -> list[str]:
    """Check if domain has MX records. Returns list of MX hosts or empty."""
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        return [str(r.exchange).rstrip(".") for r in answers]
    except Exception:
        return []


def verify_smtp(email: str, mx_host: str = "", timeout: int = 8) -> str:
    """Verify email via SMTP RCPT TO (no email sent).

    Returns:
        "accepted" — server accepted the recipient (250)
        "rejected" — server rejected the recipient (550+)
        "unknown"  — can't determine (connection failed, timeout, etc.)
    """
    domain = email.split("@")[1] if "@" in email else ""
    if not domain:
        return "rejected"

    if not mx_host:
        mx_hosts = verify_mx(domain)
        if not mx_hosts:
            return "rejected"
        mx_host = mx_hosts[0]

    try:
        smtp = smtplib.SMTP(timeout=timeout)
        smtp.connect(mx_host, 25)
        smtp.helo("verify.local")
        smtp.mail("verify@verify.local")
        code, _ = smtp.rcpt(email)
        smtp.quit()
        if code == 250:
            return "accepted"
        if code >= 550:
            return "rejected"
        return "unknown"
    except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError,
            socket.timeout, socket.gaierror, ConnectionRefusedError, OSError):
        return "unknown"
    except Exception:
        return "unknown"


def verify_email_full(email: str) -> dict:
    """Full verification: MX + SMTP.

    Returns dict with: email, valid, mx_ok, smtp_status, mx_host
    smtp_status is "accepted", "rejected", or "unknown"
    """
    domain = email.split("@")[1] if "@" in email else ""
    result = {"email": email, "valid": False, "mx_ok": False, "smtp_status": "unknown", "mx_host": ""}

    if not domain or is_junk_email(email):
        result["smtp_status"] = "rejected"
        return result

    mx_hosts = verify_mx(domain)
    if not mx_hosts:
        result["smtp_status"] = "rejected"
        return result

    result["mx_ok"] = True
    result["mx_host"] = mx_hosts[0]

    smtp_status = verify_smtp(email, mx_hosts[0])
    result["smtp_status"] = smtp_status
    # Valid if accepted OR unknown (fail-open for unknown, but score reflects it)
    result["valid"] = smtp_status != "rejected"

    return result


def verify_batch(emails: list[dict], timeout: int = 5) -> list[dict]:
    """Verify a batch of emails, grouping by domain for efficiency.

    Modifies each dict in-place: adds 'verified' ("accepted"/"rejected"/"unknown")
    and updates 'score'. Returns only non-rejected emails.
    """
    # Group by domain to share MX lookups
    domain_mx = {}  # domain -> list[mx_host] or None
    for item in emails:
        domain = item["email"].split("@")[1] if "@" in item["email"] else ""
        if domain not in domain_mx:
            domain_mx[domain] = verify_mx(domain)

    results = []
    for item in emails:
        domain = item["email"].split("@")[1] if "@" in item["email"] else ""
        mx_hosts = domain_mx.get(domain, [])

        if not mx_hosts:
            item["verified"] = "rejected"
        else:
            item["verified"] = verify_smtp(item["email"], mx_hosts[0], timeout=timeout)

        # Update score with verification status
        item["score"] = score_email(item["email"], verified=item["verified"], source=item.get("source", ""))

        if item["verified"] != "rejected":
            results.append(item)
        time.sleep(random.uniform(0.2, 0.5))

    return results


# ─── Strategy 1: Hunter.io API ──────────────────────────────────────────────

def strategy_hunter_io(domain: str) -> list[dict]:
    """Find emails via Hunter.io domain search (free tier: 25 searches/month)."""
    api_key = os.getenv("HUNTER_API_KEY", "")
    if not api_key or not domain:
        return []

    try:
        resp = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": api_key},
            timeout=10,
        )
        if resp.status_code != 200:
            log.debug(f"Hunter.io returned {resp.status_code} for {domain}")
            return []

        data = resp.json().get("data", {})
        hunter_emails = data.get("emails", [])

        found = []
        for he in hunter_emails:
            email = he.get("value", "").lower()
            if not email or is_junk_email(email):
                continue
            confidence = he.get("confidence", 0)
            # Map Hunter confidence to verification status
            if confidence >= 90:
                verified = "accepted"
            elif confidence >= 50:
                verified = "unknown"
            else:
                verified = "unknown"
            found.append({
                "email": email,
                "source": "hunter_io",
                "score": score_email(email, verified=verified, source="hunter_io"),
                "verified": verified,
                "confidence": confidence,
            })

        found.sort(key=lambda x: x["score"], reverse=True)
        return found

    except Exception as e:
        log.debug(f"Hunter.io error for {domain}: {e}")
        return []


# ─── Strategy 2: Website Scraping ───────────────────────────────────────────

def strategy_website(website: str) -> list[dict]:
    """Crawl company website for emails."""
    if not website:
        return []
    if not website.startswith("http"):
        website = "https://" + website
    website = website.rstrip("/")

    found = []
    seen = set()

    for path in CONTACT_PATHS:
        url = website + path if path != "/" else website
        html = fetch_page(url)
        if html:
            for email in extract_emails_from_html(html):
                if email not in seen:
                    seen.add(email)
                    found.append({
                        "email": email,
                        "source": "website",
                        "score": score_email(email, source="website"),
                        "verified": "unknown",
                    })
        time.sleep(random.uniform(0.5, 1.5))
        if len(found) >= 5:
            break

    return found


# ─── Strategy 3: DuckDuckGo Search ──────────────────────────────────────────

def strategy_duckduckgo(company: str, extra: str = "") -> list[dict]:
    """Search DuckDuckGo for company emails using the duckduckgo-search package."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        try:
            from ddgs import DDGS
        except ImportError:
            log.warning("duckduckgo-search/ddgs package not installed, skipping DDG strategy")
            return []

    queries = [
        f'"{company}" email contact',
        f'"{company}" careers hiring email {extra}'.strip(),
    ]

    found = []
    seen = set()

    for query in queries:
        try:
            results = DDGS().text(query, max_results=5)
            for r in results:
                # Extract emails from search snippet
                body = r.get("body", "")
                for m in EMAIL_RE.findall(body):
                    m = m.lower()
                    if m not in seen and not is_junk_email(m):
                        seen.add(m)
                        found.append({
                            "email": m,
                            "source": "search_ddg",
                            "score": score_email(m, source="search"),
                            "verified": "unknown",
                        })

                # Follow the result URL and extract emails
                href = r.get("href", "")
                if href and "duckduckgo" not in href:
                    page = fetch_page(href)
                    if page:
                        for email in extract_emails_from_html(page):
                            if email not in seen:
                                seen.add(email)
                                found.append({
                                    "email": email,
                                    "source": f"search_ddg:{urlparse(href).netloc}",
                                    "score": score_email(email, source="search"),
                                    "verified": "unknown",
                                })
                    time.sleep(random.uniform(0.5, 1.0))

        except Exception as e:
            log.debug(f"DDG search error for '{query}': {e}")
            continue
        time.sleep(random.uniform(1.0, 2.0))

    return found


# ─── Strategy 4: Google Search Fallback ──────────────────────────────────────

def strategy_google_search(company: str, extra: str = "") -> list[dict]:
    """Search Google for company emails using googlesearch-python."""
    try:
        from googlesearch import search as google_search
    except ImportError:
        log.warning("googlesearch-python package not installed, skipping Google strategy")
        return []

    query = f'"{company}" email contact {extra}'.strip()
    found = []
    seen = set()

    try:
        urls = list(google_search(query, num_results=5, lang="en"))
    except Exception as e:
        log.debug(f"Google search error: {e}")
        return []

    for url in urls[:5]:
        try:
            page = fetch_page(url)
            if page:
                for email in extract_emails_from_html(page):
                    if email not in seen:
                        seen.add(email)
                        found.append({
                            "email": email,
                            "source": f"search_google:{urlparse(url).netloc}",
                            "score": score_email(email, source="search"),
                            "verified": "unknown",
                        })
        except Exception:
            continue
        time.sleep(random.uniform(0.5, 1.0))

    return found


# ─── Strategy 5: Person-Name Email Patterns ─────────────────────────────────

def strategy_person_patterns(author_name: str, domain: str) -> list[dict]:
    """Generate person-specific email guesses from a name.

    Given "John Doe" and "company.com", tries:
      john@, johndoe@, john.doe@, jdoe@, j.doe@, doe.john@, doej@
    """
    if not author_name or not domain:
        return []

    # Clean the name
    name = author_name.strip()
    # Remove titles/suffixes
    name = re.sub(r'\b(dr|mr|mrs|ms|prof|sir|jr|sr|ii|iii|iv)\b\.?', '', name, flags=re.IGNORECASE)
    parts = name.strip().split()
    # Filter out single chars and non-alpha
    parts = [re.sub(r'[^a-z]', '', p.lower()) for p in parts]
    parts = [p for p in parts if len(p) >= 2]

    if len(parts) < 2:
        return []

    first = parts[0]
    last = parts[-1]

    patterns = [
        first,                    # john@
        f"{first}{last}",         # johndoe@
        f"{first}.{last}",        # john.doe@
        f"{first[0]}{last}",      # jdoe@
        f"{first[0]}.{last}",     # j.doe@
        f"{last}{first[0]}",      # doej@
        f"{last}.{first}",        # doe.john@
        f"{last}",                # doe@
    ]
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for p in patterns:
        if p not in seen:
            seen.add(p)
            unique.append(p)

    return [{
        "email": f"{p}@{domain}",
        "source": "person_pattern",
        "score": score_email(f"{p}@{domain}", source="person_pattern"),
        "verified": "unknown",
    } for p in unique]


# ─── Strategy 6: Generic Email Patterns ─────────────────────────────────────

def strategy_generic_patterns(domain: str) -> list[dict]:
    """Generate common email patterns for a domain."""
    if not domain:
        return []

    all_prefixes = OUTREACH_PREFIXES + GENERIC_PREFIXES
    return [{
        "email": f"{prefix}@{domain}",
        "source": "pattern_guess",
        "score": score_email(f"{prefix}@{domain}", source="pattern_guess") - 10,
        "verified": "unknown",
    } for prefix in all_prefixes]


# ─── Strategy 7: Domain Inference ────────────────────────────────────────────

def infer_domain(company: str) -> str | None:
    """Infer company domain from company name when no website is provided.

    Tries common TLDs, then uses search to find the company website.
    Returns domain string or None.
    """
    if not company:
        return None

    # Clean company name: remove suffixes and non-alphanumeric
    clean = company.lower()
    clean = re.sub(r'\b(pvt|ltd|llp|inc|llc|corp|corporation|technologies|tech|health|labs|ai|co|company)\b', '', clean)
    clean = re.sub(r'[^a-z0-9]', '', clean).strip()

    if not clean or len(clean) < 2:
        return None

    # Try common TLDs
    tlds = [".com", ".io", ".ai", ".in", ".co", ".health", ".org", ".tech"]
    for tld in tlds:
        domain = f"{clean}{tld}"
        if verify_mx(domain):
            log.debug(f"Inferred domain via MX: {domain}")
            return domain

    # Fallback: search for company website
    try:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            from ddgs import DDGS
        results = DDGS().text(f'"{company}" official website', max_results=3)
        for r in results:
            href = r.get("href", "")
            if href:
                parsed = urlparse(href)
                domain = parsed.netloc.replace("www.", "")
                if domain and domain not in JUNK_DOMAINS and verify_mx(domain):
                    log.debug(f"Inferred domain via search: {domain}")
                    return domain
    except Exception:
        pass

    return None
