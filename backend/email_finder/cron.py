#!/usr/bin/env python3
"""
Automated Email Finder — Cron Job

Runs periodically to find and verify emails for posts and startup leads
that don't have emails yet.

Uses shared strategies from strategies.py with full SMTP verification.

Usage:
    python -m email_finder.cron                     # Run once, 20 leads
    python -m email_finder.cron --max 50            # Run once, 50 leads
    python -m email_finder.cron --target posts      # Only posts
    python -m email_finder.cron --target leads      # Only startup leads
    python -m email_finder.cron --target both       # Both (default)
    python -m email_finder.cron --verify-only       # Re-verify existing emails
"""

import re
import time
import random
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

from email_finder.strategies import (
    strategy_hunter_io,
    strategy_website,
    strategy_duckduckgo,
    strategy_google_search,
    strategy_person_patterns,
    strategy_generic_patterns,
    infer_domain,
    extract_domain,
    score_email,
    verify_mx,
    verify_smtp,
    verify_email_full,
    verify_batch,
    is_junk_email,
    OUTREACH_PREFIXES,
)

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


# ─── Main: Find emails for one company (with full verification) ──────────────

def find_verified_emails(
    company: str,
    website: str = "",
    location: str = "",
    linkedin_url: str = "",
    author_name: str = "",
) -> list[dict]:
    """Find and verify emails for a company. Returns ranked list of verified emails."""

    all_emails = {}  # email -> {email, source, ...}

    def _collect(items):
        for item in items:
            if item["email"] not in all_emails:
                all_emails[item["email"]] = item

    domain = extract_domain(website)

    # Infer domain if not available
    if not domain and company:
        inferred = infer_domain(company)
        if inferred:
            domain = inferred
            log.info(f"  Inferred domain for {company}: {domain}")

    # Strategy 1: Hunter.io
    if domain:
        _collect(strategy_hunter_io(domain))

    # Strategy 2: Website scraping
    if website:
        _collect(strategy_website(website))

    # Strategy 3: DuckDuckGo search
    extra = location.split(",")[0] if location else ""
    _collect(strategy_duckduckgo(company, extra))

    # Strategy 4: Google search fallback
    if len(all_emails) < 2:
        _collect(strategy_google_search(company, extra))

    # Strategy 5: LinkedIn company page (follow external links)
    if linkedin_url and not all_emails:
        from email_finder.strategies import fetch_page, extract_emails_from_html
        from bs4 import BeautifulSoup
        html = fetch_page(linkedin_url)
        if html:
            soup = BeautifulSoup(html, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("http") and "linkedin.com" not in href:
                    page = fetch_page(href)
                    if page:
                        for e in extract_emails_from_html(page):
                            if e not in all_emails:
                                all_emails[e] = {
                                    "email": e, "source": "linkedin",
                                    "score": score_email(e, source="search"),
                                    "verified": "unknown",
                                }
                    if all_emails:
                        break

    # Strategy 6: Person-name patterns
    if author_name and domain:
        person_guesses = strategy_person_patterns(author_name, domain)
        # Verify person guesses via SMTP
        for item in person_guesses:
            if item["email"] not in all_emails:
                all_emails[item["email"]] = item

    # Strategy 7: Generic patterns + SMTP verify
    if domain:
        mx_hosts = verify_mx(domain)
        if mx_hosts:
            mx_host = mx_hosts[0]
            for prefix in OUTREACH_PREFIXES[:6]:
                email = f"{prefix}@{domain}"
                if email not in all_emails:
                    status = verify_smtp(email, mx_host, timeout=8)
                    if status != "rejected":
                        all_emails[email] = {
                            "email": email,
                            "source": "pattern_verified",
                            "score": score_email(email, verified=status, source="pattern_guess"),
                            "verified": status,
                        }
                    if len(all_emails) >= 5:
                        break
                time.sleep(random.uniform(0.3, 0.8))

    # Strategy 8: Domain guess (no website, no domain yet)
    if not all_emails and not domain:
        clean = re.sub(r'[^a-zA-Z0-9]', '', company.lower())
        for tld in [".com", ".in", ".io", ".co", ".ai"]:
            domain_guess = f"{clean}{tld}"
            mx = verify_mx(domain_guess)
            if mx:
                log.debug(f"  Found domain via guess: {domain_guess}")
                for prefix in OUTREACH_PREFIXES[:5]:
                    email = f"{prefix}@{domain_guess}"
                    status = verify_smtp(email, mx[0], timeout=8)
                    if status != "rejected":
                        all_emails[email] = {
                            "email": email,
                            "source": "domain_guess_verified",
                            "score": score_email(email, verified=status, source="pattern_guess"),
                            "verified": status,
                        }
                    time.sleep(random.uniform(0.3, 0.6))
                if all_emails:
                    break

    if not all_emails:
        return []

    # Verify all non-Hunter emails that haven't been SMTP-verified yet
    to_verify = [item for item in all_emails.values()
                 if item.get("verified") == "unknown" and item.get("source") != "hunter_io"]
    already_good = [item for item in all_emails.values()
                    if item.get("verified") != "unknown" or item.get("source") == "hunter_io"]

    verified = verify_batch(to_verify, timeout=8)

    # Combine and sort
    final = already_good + verified
    final.sort(key=lambda x: x["score"], reverse=True)

    # Add backward-compat fields
    for item in final:
        item["mx_ok"] = item.get("verified") != "rejected"
        item["smtp_ok"] = item.get("verified") == "accepted"

    return final


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
            results = find_verified_emails(company, website, location, linkedin_url, author_name=author)

            if results:
                best_emails = [r["email"] for r in results[:3]]
                email_str = ", ".join(best_emails)
                stats["found"] += 1
                stats["verified"] += len(results)

                log.info(f"    FOUND {len(results)} verified emails: {email_str}")
                for r in results[:3]:
                    log.info(f"      [{r['score']:2d}] {r['email']} via {r['source']} [{r.get('verified', '?')}]")

                # Save to DB
                if item_type == "post":
                    conn.execute(
                        "UPDATE posts SET email = ?, updated_at = datetime('now') WHERE id = ?",
                        (email_str, item_id),
                    )
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
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    parser = argparse.ArgumentParser(description="Email Finder Cron Job")
    parser.add_argument("--max", type=int, default=20, help="Max items to process per run")
    parser.add_argument("--target", choices=["posts", "leads", "both"], default="both")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing emails")
    parser.add_argument("--test", type=str, help="Test with a single company name")
    parser.add_argument("--website", type=str, default="", help="Website for --test")
    parser.add_argument("--author", type=str, default="", help="Author name for --test")
    args = parser.parse_args()

    if args.test:
        log.info(f"Testing: {args.test} (website: {args.website or 'none'}, author: {args.author or 'none'})")
        results = find_verified_emails(args.test, args.website, author_name=args.author)
        if results:
            log.info(f"Found {len(results)} verified emails:")
            for r in results:
                log.info(f"  [{r['score']:2d}] {r['email']} via {r['source']} [{r.get('verified', '?')}]")
        else:
            log.info("No verified emails found")
    elif args.verify_only:
        verify_existing(args.max)
    else:
        run_cron(max_items=args.max, target=args.target)
