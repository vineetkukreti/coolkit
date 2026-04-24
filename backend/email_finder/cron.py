#!/usr/bin/env python3
"""
Automated Email Finder — Cron Job

Runs periodically to find and verify emails for posts and startup leads
that don't have emails yet.

Strategies (in order of reliability):
1. Company website scraping (contact, about, careers, team pages)
2. DuckDuckGo search ("{company} email contact")
3. Google-style search via DuckDuckGo ("{company} careers hiring email")
4. LinkedIn company page scraping (if URL available)
5. Pattern generation from domain (info@, contact@, hr@, careers@)
6. SMTP envelope verification (RCPT TO check without sending)

Every found email is verified via:
- MX record check (domain accepts mail?)
- SMTP RCPT TO verification (does the mailbox exist?)

Usage:
    python email_finder_cron.py                    # Run once, 20 leads
    python email_finder_cron.py --max 50           # Run once, 50 leads
    python email_finder_cron.py --target posts     # Only posts
    python email_finder_cron.py --target leads     # Only startup leads
    python email_finder_cron.py --target both      # Both (default)
    python email_finder_cron.py --verify-only      # Re-verify existing emails
"""

import re
import dns.resolver
import smtplib
import socket
import time
import random
import sqlite3
import requests
import logging
from urllib.parse import urljoin, urlparse, quote_plus
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime

# ─── Logging ─────────────────────────────────────────────────────────────────

LOG_DIR = Path("data/logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "email_finder.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("email_finder")

# ─── Config ──────────────────────────────────────────────────────────────────

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE)

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

CONTACT_PATHS = [
    "/contact", "/contact-us", "/contactus",
    "/about", "/about-us", "/aboutus",
    "/careers", "/jobs", "/career", "/hiring", "/join-us", "/work-with-us",
    "/team", "/our-team", "/people", "/leadership",
    "/support", "/help",
    "/",
]

# Email prefixes to try for pattern generation (ordered by outreach value)
OUTREACH_PREFIXES = ["careers", "hr", "hiring", "jobs", "info", "contact", "hello", "team", "people", "admin"]
GENERIC_PREFIXES = ["support", "office", "business", "general"]


def _headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


# ─── Email Validation ────────────────────────────────────────────────────────

def _is_junk(email: str) -> bool:
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
    # Skip if local part is too long or mostly numbers
    if len(local) > 30:
        return True
    digits = sum(1 for c in local if c.isdigit())
    if len(local) > 4 and digits / len(local) > 0.6:
        return True
    return False


def verify_mx(domain: str) -> list[str]:
    """Check if domain has MX records. Returns list of MX hosts or empty."""
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        return [str(r.exchange).rstrip(".") for r in answers]
    except Exception:
        return []


def verify_smtp(email: str, mx_host: str = "", timeout: int = 10) -> bool:
    """Verify email exists via SMTP RCPT TO (no email actually sent).

    Returns True if the server accepts the recipient, False if rejected,
    True if we can't determine (fail-open to avoid losing valid emails).
    """
    domain = email.split("@")[1] if "@" in email else ""
    if not domain:
        return False

    # Get MX host if not provided
    if not mx_host:
        mx_hosts = verify_mx(domain)
        if not mx_hosts:
            return False
        mx_host = mx_hosts[0]

    try:
        smtp = smtplib.SMTP(timeout=timeout)
        smtp.connect(mx_host, 25)
        smtp.helo("verify.local")
        smtp.mail("verify@verify.local")
        code, _ = smtp.rcpt(email)
        smtp.quit()
        # 250 = accepted, 550/551/552/553 = rejected
        if code == 250:
            return True
        if code >= 550:
            return False
        return True  # unknown response, assume valid
    except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError,
            socket.timeout, socket.gaierror, ConnectionRefusedError, OSError):
        return True  # can't connect = fail open (many servers block port 25)
    except Exception:
        return True  # fail open


def verify_email_full(email: str) -> dict:
    """Full verification: MX + SMTP. Returns {valid, mx_ok, smtp_ok, mx_host}."""
    domain = email.split("@")[1] if "@" in email else ""
    result = {"email": email, "valid": False, "mx_ok": False, "smtp_ok": False, "mx_host": ""}

    if not domain or _is_junk(email):
        return result

    mx_hosts = verify_mx(domain)
    if not mx_hosts:
        return result

    result["mx_ok"] = True
    result["mx_host"] = mx_hosts[0]

    smtp_ok = verify_smtp(email, mx_hosts[0])
    result["smtp_ok"] = smtp_ok
    result["valid"] = smtp_ok

    return result


# ─── Email Extraction ────────────────────────────────────────────────────────

def _extract_emails_from_html(html: str) -> set:
    """Extract emails from HTML via mailto links and text regex."""
    soup = BeautifulSoup(html, "lxml")
    emails = set()

    # mailto links
    for a in soup.find_all("a", href=True):
        if "mailto:" in a["href"]:
            email = a["href"].split("mailto:")[1].split("?")[0].strip().lower()
            if email and not _is_junk(email):
                emails.add(email)

    # Text content
    text = soup.get_text(separator=" ")
    for m in EMAIL_RE.findall(text):
        m = m.lower()
        if not _is_junk(m):
            emails.add(m)

    return emails


def _fetch(url: str, timeout: int = 10) -> str | None:
    try:
        resp = requests.get(url, headers=_headers(), timeout=timeout, allow_redirects=True)
        if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
            return resp.text
    except Exception:
        pass
    return None


# ─── Strategy 1: Website Scraping ────────────────────────────────────────────

def strategy_website(website: str) -> list[str]:
    """Crawl company website for emails."""
    if not website:
        return []
    if not website.startswith("http"):
        website = "https://" + website
    website = website.rstrip("/")

    found = set()
    for path in CONTACT_PATHS:
        url = website + path if path != "/" else website
        html = _fetch(url)
        if html:
            found.update(_extract_emails_from_html(html))
        time.sleep(random.uniform(0.5, 1.5))
        if len(found) >= 5:
            break
    return list(found)


# ─── Strategy 2: DuckDuckGo Search ──────────────────────────────────────────

def strategy_duckduckgo(company: str, extra: str = "") -> list[str]:
    """Search DuckDuckGo for company emails."""
    queries = [
        f'"{company}" email contact',
        f'"{company}" careers hiring email {extra}'.strip(),
        f'"{company}" hr recruitment email',
    ]
    found = set()

    for query in queries:
        try:
            resp = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers=_headers(),
                timeout=10,
            )
            if resp.status_code != 200:
                continue

            # Extract from search results
            found.update(_extract_emails_from_html(resp.text))

            # Follow top 2 result links
            soup = BeautifulSoup(resp.text, "lxml")
            for link in soup.select("a.result__a")[:2]:
                href = link.get("href", "")
                if href and "duckduckgo" not in href:
                    page = _fetch(href)
                    if page:
                        found.update(_extract_emails_from_html(page))
                    time.sleep(random.uniform(0.5, 1.0))

        except Exception:
            continue
        time.sleep(random.uniform(1.5, 3.0))

    return list(found)


# ─── Strategy 3: Pattern Generation + Verification ──────────────────────────

def strategy_patterns(company: str, website: str) -> list[str]:
    """Generate common email patterns and verify which ones exist."""
    if not website:
        return []

    if not website.startswith("http"):
        website = "https://" + website
    domain = urlparse(website).netloc
    if not domain:
        return []
    if domain.startswith("www."):
        domain = domain[4:]

    # Check domain has MX
    mx_hosts = verify_mx(domain)
    if not mx_hosts:
        return []

    mx_host = mx_hosts[0]
    verified = []

    # Try outreach-valuable prefixes first, then generic
    for prefix in OUTREACH_PREFIXES + GENERIC_PREFIXES:
        email = f"{prefix}@{domain}"
        if verify_smtp(email, mx_host, timeout=8):
            verified.append(email)
            if len(verified) >= 3:
                break
        time.sleep(random.uniform(0.3, 0.8))

    return verified


# ─── Strategy 4: LinkedIn Company Page ───────────────────────────────────────

def strategy_linkedin_page(linkedin_url: str) -> list[str]:
    """Try to get emails from LinkedIn company page (public view)."""
    if not linkedin_url:
        return []
    # LinkedIn blocks scraping, but sometimes company websites are linked
    # and we can follow those
    html = _fetch(linkedin_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    # Look for external website links
    found = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and "linkedin.com" not in href:
            page = _fetch(href)
            if page:
                found.update(_extract_emails_from_html(page))
            if found:
                break
    return list(found)


# ─── Score & Rank Emails ─────────────────────────────────────────────────────

def score_email(email: str) -> int:
    """Score email for outreach quality."""
    email = email.lower()
    local = email.split("@")[0]
    domain = email.split("@")[1] if "@" in email else ""
    score = 10

    # Career/HR emails = gold
    if any(local.startswith(p) for p in ["hr", "careers", "hiring", "jobs", "recruit"]):
        score += 30
    # Contact emails = great
    elif any(local.startswith(p) for p in ["contact", "info", "hello", "team"]):
        score += 20
    # Named person emails
    elif "." in local:  # john.doe@company.com
        score += 15
    # Admin/generic
    elif any(local.startswith(p) for p in ["admin", "office", "business"]):
        score += 10

    # Company domain > generic
    generic = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "protonmail.com"}
    if domain not in generic:
        score += 10

    return score


# ─── Main: Find emails for one company ──────────────────────────────────────

def find_verified_emails(
    company: str,
    website: str = "",
    location: str = "",
    linkedin_url: str = "",
) -> list[dict]:
    """Find and verify emails for a company. Returns ranked list of verified emails."""

    all_emails = set()
    sources = {}  # email -> source strategy

    # Strategy 1: Website scraping (most reliable)
    if website:
        for e in strategy_website(website):
            all_emails.add(e)
            sources[e] = "website"

    # Strategy 2: DuckDuckGo search
    extra = location.split(",")[0] if location else ""
    for e in strategy_duckduckgo(company, extra):
        if e not in all_emails:
            all_emails.add(e)
            sources[e] = "search"

    # Strategy 3: LinkedIn page
    if linkedin_url and not all_emails:
        for e in strategy_linkedin_page(linkedin_url):
            if e not in all_emails:
                all_emails.add(e)
                sources[e] = "linkedin"

    # Strategy 4: Pattern generation + SMTP verify (always try if we have a website)
    if website:
        for e in strategy_patterns(company, website):
            if e not in all_emails:
                all_emails.add(e)
                sources[e] = "pattern_verified"

    # Strategy 5: If we have a company name but no website, try to find the domain first
    if not all_emails and not website:
        # Try common domain patterns: company.com, companyname.com
        clean = re.sub(r'[^a-zA-Z0-9]', '', company.lower())
        for domain_guess in [f"{clean}.com", f"{clean}.in", f"{clean}.io", f"{clean}.co"]:
            mx = verify_mx(domain_guess)
            if mx:
                log.debug(f"  Found domain via guess: {domain_guess}")
                for prefix in OUTREACH_PREFIXES[:5]:
                    email = f"{prefix}@{domain_guess}"
                    if verify_smtp(email, mx[0], timeout=8):
                        all_emails.add(email)
                        sources[email] = "domain_guess_verified"
                    time.sleep(random.uniform(0.3, 0.6))
                if all_emails:
                    break

    if not all_emails:
        return []

    # Verify all found emails
    verified = []
    for email in all_emails:
        v = verify_email_full(email)
        if v["valid"]:
            verified.append({
                "email": email,
                "source": sources.get(email, "unknown"),
                "score": score_email(email),
                "mx_ok": v["mx_ok"],
                "smtp_ok": v["smtp_ok"],
            })
        else:
            log.debug(f"  Rejected {email}: mx={v['mx_ok']} smtp={v['smtp_ok']}")

    # Sort by score (best first)
    verified.sort(key=lambda x: x["score"], reverse=True)
    return verified


# ─── Cron: Process all leads/posts without emails ───────────────────────────

def run_cron(max_items: int = 20, target: str = "both"):
    """Main cron function. Finds emails for posts and/or startup leads."""
    from db import init_db
    conn = init_db()

    start_time = datetime.now()
    log.info(f"=== Email Finder Cron Started === target={target}, max={max_items}")

    stats = {"searched": 0, "found": 0, "verified": 0, "failed": 0}

    items = []

    # Collect posts without emails
    if target in ("posts", "both"):
        rows = conn.execute(
            """SELECT 'post' as type, p.id, p.author_name,
                      (SELECT j.company FROM jobs j WHERE j.post_id = p.id LIMIT 1) as company,
                      p.links as website,
                      (SELECT j.location FROM jobs j WHERE j.post_id = p.id LIMIT 1) as location,
                      NULL as linkedin_url
               FROM posts p
               WHERE (p.email IS NULL OR p.email = '')
                 AND p.is_hiring = 1
               ORDER BY
                 CASE p.domain_relevance WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
                 p.created_at DESC
               LIMIT ?""",
            (max_items,),
        ).fetchall()
        items.extend([dict(r) for r in rows])

    # Collect startup leads without emails
    if target in ("leads", "both"):
        remaining = max(0, max_items - len(items))
        if remaining > 0:
            rows = conn.execute(
                """SELECT 'lead' as type, id, company_name as company,
                          website, location, linkedin_url, NULL as author_name, NULL as links
                   FROM startup_leads
                   WHERE (email IS NULL OR email = '')
                   ORDER BY
                     CASE WHEN website IS NOT NULL AND website != '' THEN 0 ELSE 1 END,
                     id
                   LIMIT ?""",
                (remaining,),
            ).fetchall()
            items.extend([dict(r) for r in rows])

    log.info(f"Processing {len(items)} items without emails")

    # Dedupe by company name
    seen_companies = set()

    for i, item in enumerate(items):
        item_type = item["type"]
        item_id = item["id"]
        company = item.get("company") or ""
        author = item.get("author_name") or ""

        # Try to get company from author name
        if not company and author:
            if any(kw in author for kw in ["Ltd", "Pvt", "Inc", "LLC", "Corp", "Technologies", "Health", "Labs"]):
                company = author
            else:
                content_row = conn.execute("SELECT content FROM posts WHERE id = ?", (item_id,)).fetchone()
                if content_row:
                    m = re.search(r'(?:at|@)\s+([A-Z][A-Za-z0-9\s&.]+?)(?:\s*[\n,\-|]|$)', (content_row[0] or "")[:500])
                    if m:
                        company = m.group(1).strip()

        if not company:
            log.debug(f"  [{i+1}/{len(items)}] Skipping {item_type} #{item_id} — no company name")
            continue

        # Dedupe
        ck = company.lower().strip()
        if ck in seen_companies:
            continue
        seen_companies.add(ck)

        # Extract clean website from links
        website = ""
        raw = item.get("website") or item.get("links") or ""
        if raw:
            for link in raw.split(","):
                link = link.strip()
                if link.startswith("http") and "linkedin.com" not in link and "lnkd.in" not in link:
                    website = link
                    break

        linkedin_url = item.get("linkedin_url") or ""
        location = item.get("location") or ""

        log.info(f"  [{i+1}/{len(items)}] {item_type} #{item_id}: {company} (website: {website[:40] or 'none'})")
        stats["searched"] += 1

        try:
            results = find_verified_emails(company, website, location, linkedin_url)

            if results:
                best_emails = [r["email"] for r in results[:3]]
                email_str = ", ".join(best_emails)
                stats["found"] += 1
                stats["verified"] += len(results)

                log.info(f"    FOUND {len(results)} verified emails: {email_str}")
                for r in results[:3]:
                    log.info(f"      [{r['score']:2d}] {r['email']} via {r['source']} (mx={r['mx_ok']} smtp={r['smtp_ok']})")

                # Save to DB
                if item_type == "post":
                    conn.execute(
                        "UPDATE posts SET email = ?, updated_at = datetime('now') WHERE id = ?",
                        (email_str, item_id),
                    )
                    # Also update same-company posts
                    if company:
                        conn.execute(
                            """UPDATE posts SET email = ?, updated_at = datetime('now')
                               WHERE id IN (
                                   SELECT p.id FROM posts p JOIN jobs j ON j.post_id = p.id
                                   WHERE j.company = ? AND (p.email IS NULL OR p.email = '')
                               )""",
                            (email_str, company),
                        )
                else:
                    source_str = ", ".join(set(r["source"] for r in results[:3]))
                    conn.execute(
                        """UPDATE startup_leads
                           SET email = ?, notes = COALESCE(notes || char(10), '') || ?,
                               updated_at = datetime('now')
                           WHERE id = ?""",
                        (email_str, f"[cron {datetime.now():%Y-%m-%d}] {len(results)} emails via {source_str}", item_id),
                    )
                conn.commit()
            else:
                stats["failed"] += 1
                log.info(f"    No verified emails found")

        except Exception as e:
            stats["failed"] += 1
            log.error(f"    ERROR: {e}")

        # Rate limit
        time.sleep(random.uniform(2, 5))

    elapsed = (datetime.now() - start_time).total_seconds()
    log.info(f"=== Cron Complete === {stats['searched']} searched, {stats['found']} found, "
             f"{stats['verified']} verified emails, {stats['failed']} failed, {elapsed:.0f}s elapsed")

    conn.close()
    return stats


# ─── Verify existing emails ─────────────────────────────────────────────────

def verify_existing(max_items: int = 50):
    """Re-verify emails already in the DB. Remove invalid ones."""
    from db import init_db
    conn = init_db()

    log.info(f"=== Verifying existing emails (max {max_items}) ===")

    rows = conn.execute(
        """SELECT 'post' as type, id, email FROM posts
           WHERE email IS NOT NULL AND email != ''
           UNION ALL
           SELECT 'lead' as type, id, email FROM startup_leads
           WHERE email IS NOT NULL AND email != ''
           LIMIT ?""",
        (max_items,),
    ).fetchall()

    invalid_count = 0
    for row in rows:
        row = dict(row)
        emails = [e.strip() for e in row["email"].split(",")]
        valid_emails = []
        for email in emails:
            v = verify_email_full(email)
            if v["valid"]:
                valid_emails.append(email)
            else:
                log.info(f"  INVALID: {email} (type={row['type']} id={row['id']})")
                invalid_count += 1

        if len(valid_emails) < len(emails):
            new_str = ", ".join(valid_emails) if valid_emails else ""
            if row["type"] == "post":
                conn.execute("UPDATE posts SET email = ? WHERE id = ?", (new_str or None, row["id"]))
            else:
                conn.execute("UPDATE startup_leads SET email = ? WHERE id = ?", (new_str or None, row["id"]))

        time.sleep(random.uniform(0.2, 0.5))

    conn.commit()
    log.info(f"=== Verified {len(rows)} emails, {invalid_count} removed ===")
    conn.close()


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Email Finder Cron Job")
    parser.add_argument("--max", type=int, default=20, help="Max items to process per run")
    parser.add_argument("--target", choices=["posts", "leads", "both"], default="both")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing emails")
    parser.add_argument("--test", type=str, help="Test with a single company name")
    parser.add_argument("--website", type=str, default="", help="Website for --test")
    args = parser.parse_args()

    if args.test:
        log.info(f"Testing: {args.test} (website: {args.website or 'none'})")
        results = find_verified_emails(args.test, args.website)
        if results:
            log.info(f"Found {len(results)} verified emails:")
            for r in results:
                log.info(f"  [{r['score']:2d}] {r['email']} via {r['source']} mx={r['mx_ok']} smtp={r['smtp_ok']}")
        else:
            log.info("No verified emails found")
    elif args.verify_only:
        verify_existing(args.max)
    else:
        run_cron(max_items=args.max, target=args.target)
