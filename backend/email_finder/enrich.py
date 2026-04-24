#!/usr/bin/env python3
"""
Email Enrichment Engine for Startup Leads.

Finds contact/career emails for companies by:
1. Scraping the company website (contact, about, careers, team pages)
2. Searching DuckDuckGo for "{company} email contact"
3. Searching for "{company} careers email"
4. Extracting all emails via regex, scoring & deduplicating

Usage:
    from enrich_emails import enrich_leads
    enriched = enrich_leads(conn, max_leads=50, on_progress=callback)
"""

import re
import time
import random
import sqlite3
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from pathlib import Path

# ─── Config ──────────────────────────────────────────────────────────────────

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# Pages most likely to contain emails
CONTACT_PATHS = [
    "/contact", "/contact-us", "/contactus", "/contact.html",
    "/about", "/about-us", "/aboutus", "/about.html",
    "/careers", "/jobs", "/career", "/hiring",
    "/team", "/our-team", "/people", "/leadership",
    "/support", "/help",
    "/",  # homepage fallback
]

# Email regex — catches most valid emails
EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# Junk emails to skip
JUNK_PATTERNS = [
    "example.com", "test.com", "email.com", "domain.com", "yourcompany",
    "sentry.io", "wixpress.com", "googleapis.com", "cloudflare",
    "gravatar.com", "wordpress.com", "w3.org", "schema.org",
    "facebook.com", "twitter.com", "google.com", "github.com", "duckduckgo.com",
    "jquery.com", "bootstrap", "fontawesome", "tailwindcss",
    "placeholder", "noreply", "no-reply", "donotreply",
    "webpack", "localhost", "0.0.0.0",
    ".png", ".jpg", ".gif", ".svg", ".css", ".js",
]

# Preferred email patterns (scored higher)
GOOD_PREFIXES = [
    "hr@", "careers@", "hiring@", "jobs@", "recruit",
    "contact@", "info@", "hello@", "team@", "support@",
    "admin@", "office@", "business@", "general@",
    "ceo@", "founder@", "cto@",
]


def _random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _is_junk_email(email: str) -> bool:
    """Filter out obviously fake/system emails."""
    email_lower = email.lower()
    if len(email) < 6 or len(email) > 80:
        return True
    if any(j in email_lower for j in JUNK_PATTERNS):
        return True
    # Skip emails that are just hashes or random strings
    local_part = email_lower.split("@")[0]
    if len(local_part) > 30:
        return True
    # Skip if local part is mostly numbers
    digits = sum(1 for c in local_part if c.isdigit())
    if len(local_part) > 4 and digits / len(local_part) > 0.6:
        return True
    return False


def _score_email(email: str) -> int:
    """Score an email — higher = more useful for outreach."""
    email_lower = email.lower()
    score = 10  # base score

    # Prefer career/contact emails
    for prefix in GOOD_PREFIXES:
        if email_lower.startswith(prefix) or prefix.rstrip("@") in email_lower:
            score += 20
            break

    # Prefer company domains over generic
    domain = email_lower.split("@")[1] if "@" in email_lower else ""
    generic_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "protonmail.com", "aol.com"]
    if domain in generic_domains:
        score -= 5  # still useful, just less so
    else:
        score += 10  # company domain = gold

    # Named person emails are valuable
    if "." in email_lower.split("@")[0]:  # e.g. john.doe@company.com
        score += 5

    return score


def _extract_emails_from_html(html: str) -> list[str]:
    """Extract and deduplicate emails from HTML content."""
    # Also check mailto: links
    soup = BeautifulSoup(html, "lxml")

    emails = set()

    # From mailto links
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "mailto:" in href:
            email = href.split("mailto:")[1].split("?")[0].strip()
            if email:
                emails.add(email.lower())

    # From raw text
    text = soup.get_text(separator=" ")
    for match in EMAIL_RE.findall(text):
        emails.add(match.lower())

    # From href/src attributes (sometimes emails in data attributes)
    for tag in soup.find_all(True):
        for attr_val in tag.attrs.values():
            if isinstance(attr_val, str):
                for match in EMAIL_RE.findall(attr_val):
                    emails.add(match.lower())

    # Filter junk
    return [e for e in emails if not _is_junk_email(e)]


def _fetch_page(url: str, timeout: int = 10) -> str | None:
    """Fetch a page, return HTML or None."""
    try:
        resp = requests.get(url, headers=_random_headers(), timeout=timeout, allow_redirects=True)
        if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
            return resp.text
    except Exception:
        pass
    return None


# ─── Strategy 1: Scrape company website ─────────────────────────────────────

def scrape_website_emails(website: str) -> list[dict]:
    """Crawl a company website for emails. Returns list of {email, source, score}."""
    if not website:
        return []

    # Normalize URL
    if not website.startswith("http"):
        website = "https://" + website
    website = website.rstrip("/")

    found = []
    seen_emails = set()

    for path in CONTACT_PATHS:
        url = website + path if path != "/" else website
        html = _fetch_page(url)
        if not html:
            continue

        emails = _extract_emails_from_html(html)
        for email in emails:
            if email not in seen_emails:
                seen_emails.add(email)
                found.append({
                    "email": email,
                    "source": f"website:{path}",
                    "score": _score_email(email),
                })

        # Don't hammer the server
        time.sleep(random.uniform(0.5, 1.5))

        # Stop early if we found good emails
        if len(found) >= 5:
            break

    return found


# ─── Strategy 2: DuckDuckGo search ──────────────────────────────────────────

def search_duckduckgo_emails(company_name: str, extra_terms: str = "") -> list[dict]:
    """Search DuckDuckGo for company emails."""
    queries = [
        f"{company_name} contact email",
        f"{company_name} careers email {extra_terms}".strip(),
    ]

    found = []
    seen_emails = set()

    for query in queries:
        try:
            resp = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers=_random_headers(),
                timeout=10,
            )
            if resp.status_code != 200:
                continue

            # Extract emails from search results page
            emails = _extract_emails_from_html(resp.text)
            for email in emails:
                if email not in seen_emails:
                    seen_emails.add(email)
                    found.append({
                        "email": email,
                        "source": f"duckduckgo:{query[:40]}",
                        "score": _score_email(email),
                    })

            # Also follow top result links
            soup = BeautifulSoup(resp.text, "lxml")
            links = soup.select("a.result__a")[:3]  # top 3 results
            for link in links:
                href = link.get("href", "")
                if not href or "duckduckgo" in href:
                    continue
                page_html = _fetch_page(href)
                if page_html:
                    for email in _extract_emails_from_html(page_html):
                        if email not in seen_emails:
                            seen_emails.add(email)
                            found.append({
                                "email": email,
                                "source": f"search_result:{urlparse(href).netloc}",
                                "score": _score_email(email),
                            })
                time.sleep(random.uniform(0.5, 1.0))

        except Exception:
            continue

        time.sleep(random.uniform(1.0, 2.0))

    return found


# ─── Strategy 3: Common email pattern guessing ──────────────────────────────

def guess_common_emails(company_name: str, website: str) -> list[dict]:
    """Generate common email patterns based on company domain."""
    if not website:
        return []

    # Extract domain
    if not website.startswith("http"):
        website = "https://" + website
    domain = urlparse(website).netloc
    if not domain:
        return []
    # Strip www.
    if domain.startswith("www."):
        domain = domain[4:]

    prefixes = ["info", "contact", "hello", "hr", "careers", "hiring", "jobs", "team", "admin"]
    guesses = []
    for prefix in prefixes:
        email = f"{prefix}@{domain}"
        guesses.append({
            "email": email,
            "source": "pattern_guess",
            "score": _score_email(email) - 10,  # lower score since unverified
        })

    return guesses


# ─── Verify email exists (lightweight) ───────────────────────────────────────

def _verify_email_quick(email: str) -> bool:
    """Quick check - just verify the domain has MX records."""
    import subprocess
    domain = email.split("@")[1] if "@" in email else ""
    if not domain:
        return False
    try:
        result = subprocess.run(
            ["dig", "+short", "MX", domain],
            capture_output=True, text=True, timeout=5,
        )
        return bool(result.stdout.strip())
    except Exception:
        return True  # assume valid if we can't check


# ─── Main enrichment function ────────────────────────────────────────────────

def find_emails_for_company(company_name: str, website: str = "", location: str = "") -> list[dict]:
    """Find emails for a single company using all strategies.
    Returns sorted list of {email, source, score, verified}."""

    all_found = []
    seen = set()

    # Strategy 1: Scrape website (most reliable)
    if website:
        for item in scrape_website_emails(website):
            if item["email"] not in seen:
                seen.add(item["email"])
                all_found.append(item)

    # Strategy 2: Web search (finds emails from job boards, reviews, etc.)
    extra = location.split(",")[0] if location else ""
    for item in search_duckduckgo_emails(company_name, extra):
        if item["email"] not in seen:
            seen.add(item["email"])
            all_found.append(item)

    # Strategy 3: Pattern guessing (last resort)
    if not all_found and website:
        for item in guess_common_emails(company_name, website):
            if item["email"] not in seen:
                seen.add(item["email"])
                all_found.append(item)

    # Sort by score (best first)
    all_found.sort(key=lambda x: x["score"], reverse=True)

    # Quick MX verification for top results
    for item in all_found[:5]:
        item["verified"] = _verify_email_quick(item["email"])

    return all_found


# ─── Bulk enrichment with DB ─────────────────────────────────────────────────

def enrich_leads(
    conn: sqlite3.Connection,
    max_leads: int = 50,
    target: str = "startup_leads",  # "startup_leads" or "posts"
    on_progress=None,
):
    """Bulk enrich leads that don't have emails.

    Args:
        conn: DB connection
        max_leads: max companies to process
        target: which table to enrich
        on_progress: callback(dict) for progress updates

    Returns:
        dict with {enriched, skipped, failed, total_emails_found}
    """
    def _emit(data):
        if on_progress:
            on_progress(data)

    results = {"enriched": 0, "skipped": 0, "failed": 0, "total_emails_found": 0}

    if target == "startup_leads":
        rows = conn.execute(
            """SELECT id, company_name, website, location, email
               FROM startup_leads
               WHERE (email IS NULL OR email = '')
               ORDER BY
                 CASE WHEN website IS NOT NULL AND website != '' THEN 0 ELSE 1 END,
                 id
               LIMIT ?""",
            (max_leads,),
        ).fetchall()
    else:
        # Posts without emails — get company + content + links for each post
        rows = conn.execute(
            """SELECT p.id, p.author_name, p.content, p.links,
                      (SELECT j.company FROM jobs j WHERE j.post_id = p.id LIMIT 1) as company_name,
                      (SELECT j.role FROM jobs j WHERE j.post_id = p.id LIMIT 1) as role,
                      (SELECT j.location FROM jobs j WHERE j.post_id = p.id LIMIT 1) as location,
                      p.email
               FROM posts p
               WHERE (p.email IS NULL OR p.email = '')
                 AND p.is_hiring = 1
               ORDER BY
                 CASE WHEN (SELECT j2.company FROM jobs j2 WHERE j2.post_id = p.id LIMIT 1)
                      IS NOT NULL THEN 0 ELSE 1 END,
                 p.domain_relevance = 'High' DESC,
                 p.created_at DESC
               LIMIT ?""",
            (max_leads,),
        ).fetchall()

    total = len(rows)
    _emit({"type": "start", "total": total, "target": target})

    # Track companies already searched to avoid duplicate lookups
    _searched_companies = set()

    for i, row in enumerate(rows):
        row = dict(row)
        lead_id = row["id"]
        company = row.get("company_name") or ""
        location = row.get("location") or ""

        # Extract website from links (first http link that looks like a company site)
        raw_links = row.get("website") or row.get("links") or ""
        website = ""
        if raw_links:
            for link in raw_links.split(","):
                link = link.strip()
                if link.startswith("http") and "linkedin.com" not in link and "lnkd.in" not in link:
                    website = link
                    break

        # If no company name, try to extract from author or content
        if not company:
            author = row.get("author_name") or ""
            content = row.get("content") or ""
            # Use author name as company if it looks like a company (contains Ltd, Inc, etc.)
            if any(kw in author for kw in ["Ltd", "Pvt", "Inc", "LLC", "Corp", "Technologies", "Health", "Labs"]):
                company = author
            # Try to find company name from content (look for "at CompanyName" or "@ CompanyName")
            elif content:
                import re
                m = re.search(r'(?:at|@)\s+([A-Z][A-Za-z0-9\s&.]+?)(?:\s*[\n,\-|]|$)', content[:500])
                if m:
                    company = m.group(1).strip()

        # Skip if we already searched this company
        if company:
            company_key = company.lower().strip()
            if company_key in _searched_companies:
                results["skipped"] += 1
                continue
            _searched_companies.add(company_key)

        _emit({
            "type": "searching",
            "current": i + 1,
            "total": total,
            "company": company,
            "lead_id": lead_id,
        })

        if not company:
            results["skipped"] += 1
            continue

        try:
            found = find_emails_for_company(company, website, location)

            if found:
                # Pick best email(s)
                best_emails = [f["email"] for f in found[:3]]  # top 3
                email_str = ", ".join(best_emails)
                sources = [f["source"] for f in found[:3]]

                if target == "startup_leads":
                    conn.execute(
                        """UPDATE startup_leads
                           SET email = ?, notes = COALESCE(notes || char(10), '') || ?,
                               updated_at = datetime('now')
                           WHERE id = ?""",
                        (
                            email_str,
                            f"[auto] Found {len(found)} emails via {', '.join(set(s.split(':')[0] for s in sources))}",
                            lead_id,
                        ),
                    )
                else:
                    # Update this post
                    conn.execute(
                        "UPDATE posts SET email = ?, updated_at = datetime('now') WHERE id = ?",
                        (email_str, lead_id),
                    )
                    # Also update other posts from the same company that lack emails
                    if company:
                        conn.execute(
                            """UPDATE posts SET email = ?, updated_at = datetime('now')
                               WHERE id IN (
                                   SELECT p.id FROM posts p
                                   JOIN jobs j ON j.post_id = p.id
                                   WHERE j.company = ? AND (p.email IS NULL OR p.email = '')
                               )""",
                            (email_str, company),
                        )
                conn.commit()

                results["enriched"] += 1
                results["total_emails_found"] += len(found)

                _emit({
                    "type": "found",
                    "current": i + 1,
                    "total": total,
                    "company": company,
                    "lead_id": lead_id,
                    "emails": best_emails,
                    "all_count": len(found),
                    "sources": sources,
                })
            else:
                results["skipped"] += 1
                _emit({
                    "type": "not_found",
                    "current": i + 1,
                    "total": total,
                    "company": company,
                    "lead_id": lead_id,
                })

        except Exception as e:
            results["failed"] += 1
            _emit({
                "type": "error",
                "current": i + 1,
                "total": total,
                "company": company,
                "lead_id": lead_id,
                "error": str(e)[:200],
            })

        # Rate limiting
        time.sleep(random.uniform(1.5, 3.0))

    _emit({"type": "done", **results})
    return results


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    from db import init_db

    parser = argparse.ArgumentParser(description="Find emails for startup leads")
    parser.add_argument("--max", type=int, default=10, help="Max leads to process")
    parser.add_argument("--target", choices=["startup_leads", "posts"], default="startup_leads")
    parser.add_argument("--company", type=str, help="Test with a single company name")
    parser.add_argument("--website", type=str, default="", help="Company website (for --company)")
    args = parser.parse_args()

    if args.company:
        print(f"\nSearching emails for: {args.company}")
        print(f"Website: {args.website or 'none'}\n")
        results = find_emails_for_company(args.company, args.website)
        if results:
            print(f"Found {len(results)} emails:\n")
            for r in results:
                v = "MX-ok" if r.get("verified") else ""
                print(f"  [{r['score']:3d}] {r['email']:40s}  via {r['source']:30s}  {v}")
        else:
            print("No emails found.")
    else:
        conn = init_db()

        def progress(data):
            t = data.get("type", "")
            if t == "start":
                print(f"\nEnriching {data['total']} {data['target']} without emails...\n")
            elif t == "searching":
                print(f"  [{data['current']}/{data['total']}] Searching: {data['company']}...")
            elif t == "found":
                print(f"  [{data['current']}/{data['total']}] FOUND {data['all_count']} emails for {data['company']}: {', '.join(data['emails'])}")
            elif t == "not_found":
                print(f"  [{data['current']}/{data['total']}] No emails for {data['company']}")
            elif t == "error":
                print(f"  [{data['current']}/{data['total']}] ERROR {data['company']}: {data['error']}")
            elif t == "done":
                print(f"\nDone! Enriched: {data['enriched']}, Skipped: {data['skipped']}, Failed: {data['failed']}")
                print(f"Total emails found: {data['total_emails_found']}")

        enrich_leads(conn, max_leads=args.max, target=args.target, on_progress=progress)
        conn.close()
