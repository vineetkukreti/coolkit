#!/usr/bin/env python3
"""
Fast bulk email enrichment for startup leads.

Strategy per lead:
  1. If website exists → scrape it for emails (fast, ~2s)
  2. If no website → infer domain from company name via MX check
  3. Try generic patterns (careers@, info@, hr@) on the domain
  4. SMTP-verify everything — only save "accepted" or "unknown" (fail-open)

Skips slow DDG/Google search to keep speed up.
Uses ThreadPoolExecutor for parallel processing.
"""

import sys
import re
import sqlite3
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, "backend")

from email_finder.strategies import (
    extract_domain,
    infer_domain,
    strategy_website,
    strategy_generic_patterns,
    verify_batch,
    is_junk_email,
)

logging.basicConfig(level=logging.WARNING)


def find_verified_emails(company: str, website: str = "", location: str = "") -> list[dict]:
    """Find and verify emails for a single company. Fast path — no DDG/Google."""
    domain = extract_domain(website)

    # Infer domain if no website
    if not domain and company:
        domain = infer_domain(company)

    if not domain:
        return []

    all_emails = []
    seen = set()

    def collect(items):
        for item in items:
            if item["email"] not in seen and not is_junk_email(item["email"]):
                # Must match company domain
                email_domain = item["email"].rsplit("@", 1)[-1]
                if email_domain == domain:
                    seen.add(item["email"])
                    all_emails.append(item)

    # 1. Website scraping
    if website:
        collect(strategy_website(website))

    # 2. Generic patterns (careers@, info@, hr@, hello@, etc.)
    if len(all_emails) < 2:
        guesses = strategy_generic_patterns(domain)[:8]
        verified_guesses = verify_batch(guesses, timeout=5)
        collect(verified_guesses)

    # 3. Verify website-scraped emails too
    if all_emails:
        all_emails = verify_batch(all_emails, timeout=5)

    all_emails.sort(key=lambda x: x["score"], reverse=True)
    return all_emails


def process_lead(row: dict) -> dict:
    """Process a single lead. Returns result dict."""
    cid = row["id"]
    company = row["company_name"]
    website = row.get("website") or ""
    location = row.get("location") or ""

    try:
        emails = find_verified_emails(company, website, location)
        if emails:
            best = [e["email"] for e in emails[:3]]
            return {
                "id": cid,
                "company": company,
                "emails": best,
                "count": len(emails),
                "status": "found",
            }
        return {"id": cid, "company": company, "status": "none"}
    except Exception as e:
        return {"id": cid, "company": company, "status": "error", "error": str(e)[:100]}


def main():
    conn = sqlite3.connect("data/linkedin_jobs.db")
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT id, company_name, website, location
        FROM startup_leads
        WHERE (email IS NULL OR email = '')
          AND industry LIKE '%Health%'
        ORDER BY
          CASE WHEN website IS NOT NULL AND website <> '' THEN 0 ELSE 1 END,
          id
    """).fetchall()

    total = len(rows)
    print(f"Processing {total} healthcare leads (4 threads)...", flush=True)
    print(flush=True)

    found_count = 0
    processed = 0

    # Process in batches with thread pool
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(process_lead, dict(row)): dict(row) for row in rows}

        for future in as_completed(futures):
            processed += 1
            result = future.result()

            if result["status"] == "found":
                found_count += 1
                email_str = ", ".join(result["emails"])
                conn.execute(
                    'UPDATE startup_leads SET email = ?, updated_at = datetime("now") WHERE id = ?',
                    (email_str, result["id"]),
                )
                conn.commit()
                print(
                    f'[{processed}/{total}] {result["company"][:42]:<42} -> {email_str}',
                    flush=True,
                )
            elif result["status"] == "error":
                print(
                    f'[{processed}/{total}] {result["company"][:42]:<42} -> ERROR: {result["error"]}',
                    flush=True,
                )
            else:
                print(
                    f'[{processed}/{total}] {result["company"][:42]:<42} -> (none)',
                    flush=True,
                )

    print(flush=True)
    print(f"DONE: Verified emails for {found_count}/{total} healthcare leads", flush=True)
    conn.close()


if __name__ == "__main__":
    main()
