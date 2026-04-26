#!/usr/bin/env python3
"""
Email Enrichment Engine for Startup Leads & Posts.

Finds contact/career emails for companies using a multi-strategy pipeline:
1. Hunter.io API (if configured, 25 free/month)
2. Company website scraping
3. DuckDuckGo search
4. Google search fallback
5. Person-name email patterns (if author_name available)
6. Generic email patterns (info@, hr@, careers@)

All strategies are imported from strategies.py. Pattern-guessed emails
are verified via MX + SMTP before saving.

Usage:
    from email_finder.enrich import find_emails_for_company, enrich_leads
    emails = find_emails_for_company("Acme Corp", website="https://acme.com", author_name="John Doe")
    enriched = enrich_leads(conn, max_leads=50, on_progress=callback)
"""

import re
import time
import random
import sqlite3
import logging

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
    verify_batch,
)

log = logging.getLogger("email_finder")


# ─── Main: find emails for one company ───────────────────────────────────────

def find_emails_for_company(
    company_name: str,
    website: str = "",
    location: str = "",
    author_name: str = "",
) -> list[dict]:
    """Find emails for a single company using all strategies.

    Returns sorted list of {email, source, score, verified}.
    """
    all_found = []
    seen = set()

    def _collect(items):
        for item in items:
            if item["email"] not in seen:
                seen.add(item["email"])
                all_found.append(item)

    # Resolve domain early — needed by Hunter, person patterns, generic patterns
    domain = extract_domain(website)

    # If no website/domain, try to infer it
    if not domain and company_name:
        inferred = infer_domain(company_name)
        if inferred:
            domain = inferred
            log.debug(f"Inferred domain for {company_name}: {domain}")

    # Strategy 1: Hunter.io (highest confidence, uses API quota)
    if domain:
        _collect(strategy_hunter_io(domain))

    # Strategy 2: Website scraping (most reliable free method)
    if website:
        _collect(strategy_website(website))

    # Strategy 3: DuckDuckGo search
    extra = location.split(",")[0] if location else ""
    _collect(strategy_duckduckgo(company_name, extra))

    # Strategy 4: Google search fallback (only if we haven't found much yet)
    if len(all_found) < 2:
        _collect(strategy_google_search(company_name, extra))

    # Strategy 5: Person-name patterns (if we have both author name and domain)
    person_guesses = []
    if author_name and domain:
        person_guesses = strategy_person_patterns(author_name, domain)
        # Don't add to all_found yet — verify first

    # Strategy 6: Generic patterns (last resort, only if nothing found)
    generic_guesses = []
    if not all_found and domain:
        generic_guesses = strategy_generic_patterns(domain)

    # ── Verify pattern-guessed emails before adding ──
    # This is the key fix: previously guesses were saved unverified
    guesses_to_verify = (person_guesses + generic_guesses)[:8]  # limit to 8 for speed
    if guesses_to_verify:
        verified_guesses = verify_batch(guesses_to_verify, timeout=5)
        _collect(verified_guesses)

    # Sort by score (best first)
    all_found.sort(key=lambda x: x["score"], reverse=True)

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
        # Posts without emails — get company + content + links + author for each post
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
        author_name = row.get("author_name") or ""

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
            author = author_name
            content = row.get("content") or ""
            if any(kw in author for kw in ["Ltd", "Pvt", "Inc", "LLC", "Corp", "Technologies", "Health", "Labs"]):
                company = author
            elif content:
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
            found = find_emails_for_company(company, website, location, author_name)

            if found:
                # Pick best email(s)
                best_emails = [f["email"] for f in found[:3]]
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
                    conn.execute(
                        "UPDATE posts SET email = ?, updated_at = datetime('now') WHERE id = ?",
                        (email_str, lead_id),
                    )
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
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

    from db import init_db

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Find emails for startup leads")
    parser.add_argument("--max", type=int, default=10, help="Max leads to process")
    parser.add_argument("--target", choices=["startup_leads", "posts"], default="startup_leads")
    parser.add_argument("--company", type=str, help="Test with a single company name")
    parser.add_argument("--website", type=str, default="", help="Company website (for --company)")
    parser.add_argument("--author", type=str, default="", help="Author/person name (for --company)")
    args = parser.parse_args()

    if args.company:
        print(f"\nSearching emails for: {args.company}")
        print(f"Website: {args.website or 'none'}")
        print(f"Author: {args.author or 'none'}\n")
        results = find_emails_for_company(args.company, args.website, author_name=args.author)
        if results:
            print(f"Found {len(results)} emails:\n")
            for r in results:
                v = r.get("verified", "?")
                print(f"  [{r['score']:3d}] {r['email']:40s}  via {r['source']:30s}  [{v}]")
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
