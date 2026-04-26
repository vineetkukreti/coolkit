#!/usr/bin/env python3
"""
LinkedIn Hiring Post Parser
----------------------------
Searches LinkedIn posts for hiring mentions in healthcare/clinical AI domain.
Extracts author, content, emails, role, company → saves to Excel.

Usage:
    python post_parser.py
"""

import os
import re
import json
import time
import random
import urllib.request
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from config import (
    TARGET_ROLES, DOMAIN_KEYWORDS, ROLE_STEMS, DOMAIN_STEMS_HEALTHCARE,
    DOMAIN_STEMS_GENERAL, DOMAIN_STEMS, LOCATION_STEMS, ACTION_STEMS,
    EXP_STEMS, ROLE_KEYWORDS, HASHTAG_FEEDS, JOB_SEARCH_QUERIES,
    JOB_EXP_LEVELS, JOB_TYPE, build_smart_queries,
)
from extractors.text import (
    EMAIL_RE, extract_emails, extract_roles, extract_location,
    extract_experience, normalize_experience, score_domain_relevance,
    is_hiring_post, is_feed_job_post,
)
from extractors.fitness import (
    KEEP_ROLES, FALSE_POSITIVE_ROLES, is_relevant_role,
    experience_to_years, is_good_fit,
)
from llm.client import llm as _llm_client, OLLAMA_URL, OLLAMA_MODEL, GEMINI_API_KEY, GEMINI_MODEL
from llm.extraction import (
    llm_extract, llm_extract_emails, llm_deep_analyze,
    ollama_available, ollama_extract, gemini_extract,
    _parse_llm_response, _parse_deep_analysis,
    _LLM_PROMPT, _EMAIL_DEOBFUSCATION_PROMPT, _DEEP_ANALYSIS_PROMPT,
)
from db import init_db, insert_posts, post_exists, content_hash, get_stats, DedupCache

# Backward-compat: expose _get_gemini_client and global state
_get_gemini_client = _llm_client._get_gemini_client
_ollama_ok = None  # kept for any external code checking this
_gemini_ok = None
_gemini_client = None

console = Console()

# ─── Config ──────────────────────────────────────────────────────────────────

MAX_POSTS = 1000  # Total posts to collect

# ─── LLM Config ───────────────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash-lite"

# Build search queries (shuffled each run)
SEARCH_QUERIES = build_smart_queries()

# Backward-compat aliases for internal use
_ROLE_STEMS = ROLE_STEMS
_DOMAIN_STEMS_HEALTHCARE = DOMAIN_STEMS_HEALTHCARE
_DOMAIN_STEMS_GENERAL = DOMAIN_STEMS_GENERAL
_DOMAIN_STEMS = DOMAIN_STEMS
_LOCATION_STEMS = LOCATION_STEMS
_ACTION_STEMS = ACTION_STEMS
_EXP_STEMS = EXP_STEMS
_HASHTAG_FEEDS = list(HASHTAG_FEEDS)



# ─── Profile Email Extraction ─────────────────────────────────────────────────

def extract_profile_email(page, profile_url: str, on_event=None) -> str:
    """Visit a LinkedIn profile's Contact Info overlay to extract email.

    LinkedIn shows email at /in/username/overlay/contact-info/ if:
    - The user has set email as public, OR
    - You are connected with them

    Returns comma-separated emails found, or empty string.
    """
    def emit(event):
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass

    if not profile_url or "/in/" not in profile_url:
        return ""

    # Normalize URL → /in/username/overlay/contact-info/
    base = profile_url.rstrip("/").split("?")[0]
    if "/overlay/contact-info" not in base:
        contact_url = f"{base}/overlay/contact-info/"
    else:
        contact_url = base

    try:
        page.goto(contact_url, timeout=15000, wait_until="domcontentloaded")
        time.sleep(random.uniform(3, 6))

        # Extract emails from contact info modal
        emails = page.evaluate("""
        () => {
            const emails = [];

            // Strategy 1: Look for mailto links in the contact info section
            document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
                const email = a.href.replace('mailto:', '').split('?')[0].trim();
                if (email && email.includes('@')) emails.push(email);
            });

            // Strategy 2: Look for email section by icon/label
            document.querySelectorAll('section, div[class*="contact"], div[class*="pv-contact"]').forEach(section => {
                const text = section.innerText || '';
                // LinkedIn labels email sections with "Email" header
                if (/email/i.test(text)) {
                    const emailRegex = /[A-Za-z0-9._%+\\-]+@[A-Za-z0-9.\\-]+\\.[A-Za-z]{2,}/g;
                    const found = text.match(emailRegex) || [];
                    found.forEach(e => emails.push(e));
                }
            });

            // Strategy 3: Broad scan of the overlay/modal for any email
            const overlay = document.querySelector('[class*="overlay"], [class*="modal"], [role="dialog"]');
            if (overlay) {
                const text = overlay.innerText || '';
                const emailRegex = /[A-Za-z0-9._%+\\-]+@[A-Za-z0-9.\\-]+\\.[A-Za-z]{2,}/g;
                const found = text.match(emailRegex) || [];
                found.forEach(e => emails.push(e));
            }

            // Deduplicate
            return [...new Set(emails.map(e => e.toLowerCase()))];
        }
        """)

        if emails:
            result = ", ".join(emails)
            emit({"type": "profile_email", "url": profile_url, "email": result})
            return result
        return ""
    except Exception as e:
        emit({"type": "profile_error", "url": profile_url, "error": str(e)[:100]})
        return ""


def enrich_posts_with_profile_emails(page, conn, max_visits: int = 100, on_event=None) -> int:
    """Backfill emails for existing DB posts by visiting author profiles.

    Finds posts that have author_profile URL but no email, visits the profile
    contact info to extract email, and updates the DB.

    Returns number of posts enriched with new emails.
    """
    def emit(event):
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass

    # Find posts with profile URLs but no email
    rows = conn.execute(
        """SELECT id, author_name, author_profile FROM posts
           WHERE author_profile IS NOT NULL AND author_profile != ''
             AND author_profile LIKE '%/in/%'
             AND (email IS NULL OR email = '')
             AND is_hiring = 1
           ORDER BY
             CASE domain_relevance WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
             created_at DESC
           LIMIT ?""",
        (max_visits,),
    ).fetchall()

    if not rows:
        emit({"type": "info", "message": "No posts need email enrichment — all profiles visited or all have emails"})
        return 0

    emit({"type": "info", "message": f"Enricher: {len(rows)} profiles to visit for emails"})

    enriched = 0
    visited_profiles = set()

    for i, row in enumerate(rows):
        post_id = row["id"]
        author = row["author_name"] or "Unknown"
        profile_url = row["author_profile"]

        # Skip if we already visited this profile URL in this session
        profile_key = profile_url.rstrip("/").split("?")[0].lower()
        if profile_key in visited_profiles:
            continue
        visited_profiles.add(profile_key)

        emit({"type": "search", "query": f"Profile: {author[:30]}",
              "index": i + 1, "total": len(rows)})

        email = extract_profile_email(page, profile_url, on_event=on_event)

        if email:
            # Update ALL posts from this author profile
            conn.execute(
                "UPDATE posts SET email = ?, updated_at = datetime('now') WHERE author_profile = ? AND (email IS NULL OR email = '')",
                (email, row["author_profile"]),
            )
            conn.commit()
            enriched += 1
            emit({"type": "found", "sno": enriched, "author": author[:25],
                  "role": "enriched", "company": "", "email": email[:30], "domain": "profile"})
        else:
            emit({"type": "skip", "author": author[:25], "reason": "No public email on profile"})

        # Rate limit — be very gentle with profile visits (high ban risk)
        time.sleep(random.uniform(8, 15))

    emit({"type": "done", "total": enriched,
          "queries_searched": len(visited_profiles),
          "message": f"Enriched {enriched}/{len(rows)} posts with profile emails"})
    return enriched


# ─── Deep Content Extraction ─────────────────────────────────────────────────

def deep_extract_post(page, post_url: str, on_event=None) -> dict:
    """Visit a LinkedIn post/job URL and extract FULL content, emails, links, apply URL.

    Handles two URL patterns:
    - Post URLs (/posts/, /feed/update/) → full post text
    - Job URLs (/jobs/view/) → full job description

    Returns dict with: full_content, emails, links, apply_url
    """
    def emit(event):
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass

    if not post_url:
        return {}

    result = {"full_content": "", "emails": "", "links": "", "apply_url": ""}

    try:
        page.goto(post_url, timeout=20000, wait_until="domcontentloaded")
        time.sleep(random.uniform(4, 7))

        # Click "see more" / expand buttons
        try:
            btns = page.query_selector_all(
                "button[aria-label*='see more'], button[aria-label*='See more'], "
                "button.see-more-less-button, button[class*='see-more'], "
                "button[class*='show-more']"
            )
            for btn in btns[:3]:
                try:
                    btn.scroll_into_view_if_needed()
                    time.sleep(random.uniform(0.3, 0.7))
                    btn.click()
                except Exception:
                    pass
            if btns:
                time.sleep(0.8)
        except Exception:
            pass

        is_job_page = "/jobs/view/" in post_url

        # Extract full content based on page type
        extracted = page.evaluate("""
        (isJobPage) => {
            const result = { content: '', emails: [], links: [], applyUrl: '' };
            const emailRegex = /[A-Za-z0-9._%+\\-]+@[A-Za-z0-9.\\-]+\\.[A-Za-z]{2,}/g;

            if (isJobPage) {
                // LinkedIn Job page extraction
                const descEl = document.querySelector(
                    'div.jobs-description__content, ' +
                    'div.show-more-less-html__markup, ' +
                    'div[class*="description__text"], ' +
                    'div[class*="jobs-box__html-content"], ' +
                    'article'
                );
                if (descEl) result.content = descEl.innerText.trim();

                // Get title + company for context
                const titleEl = document.querySelector('h1, h2.jobs-unified-top-card__job-title');
                const companyEl = document.querySelector('a[class*="company-name"], span[class*="company-name"]');
                if (titleEl) result.content = titleEl.innerText.trim() + '\\n\\n' + result.content;

                // Apply button — look for external apply link
                const applyBtn = document.querySelector('a[href*="apply"], a.jobs-apply-button, button[aria-label*="Apply"]');
                if (applyBtn && applyBtn.href && !applyBtn.href.includes('linkedin.com')) {
                    result.applyUrl = applyBtn.href;
                }
                // Also check for "Apply on company website" links
                document.querySelectorAll('a[href]').forEach(a => {
                    if (a.innerText && /apply.*company|company.*website|external.*apply/i.test(a.innerText)) {
                        if (a.href && !a.href.includes('linkedin.com')) {
                            result.applyUrl = a.href.split('?')[0];
                        }
                    }
                });
            } else {
                // LinkedIn Post page extraction
                const postEl = document.querySelector(
                    'span[data-testid="expandable-text-box"], ' +
                    'div.feed-shared-update-v2__description, ' +
                    'div.feed-shared-inline-show-more-text, ' +
                    'article'
                );
                if (postEl) result.content = postEl.innerText.trim();
            }

            // Extract emails from full content
            if (result.content) {
                const found = result.content.match(emailRegex) || [];
                result.emails = [...new Set(found)];
            }

            // Extract mailto links
            document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
                const email = a.href.replace('mailto:', '').split('?')[0].trim();
                if (email && email.includes('@')) result.emails.push(email);
            });
            result.emails = [...new Set(result.emails)];

            // Extract external links
            document.querySelectorAll('a[href]').forEach(a => {
                const h = a.href;
                if (h && h.startsWith('http') && !h.includes('linkedin.com') && !h.startsWith('mailto:')) {
                    result.links.push(h.split('?')[0]);
                }
            });
            result.links = [...new Set(result.links)];

            return result;
        }
        """, is_job_page)

        full_content = extracted.get("content", "").strip()
        if full_content and len(full_content) > 30:
            result["full_content"] = full_content

        js_emails = extracted.get("emails", [])
        # Also run regex on the full content
        if full_content:
            regex_found = EMAIL_RE.findall(full_content)
            all_emails = list(set(js_emails + regex_found))
        else:
            all_emails = js_emails

        # LLM deobfuscation on full content
        if not all_emails and full_content:
            llm_emails = llm_extract_emails(full_content)
            all_emails.extend(llm_emails)

        if all_emails:
            result["emails"] = ", ".join(set(e.lower() for e in all_emails))

        links = extracted.get("links", [])
        if links:
            result["links"] = ", ".join(links[:10])

        result["apply_url"] = extracted.get("applyUrl", "")

        if result["emails"]:
            emit({"type": "deep_extract", "url": post_url[:50], "email": result["emails"][:40],
                  "message": f"Deep extract found email: {result['emails'][:40]}"})
        else:
            emit({"type": "deep_extract", "url": post_url[:50],
                  "message": f"Deep extract: full content ({len(full_content)} chars), no email"})

    except Exception as e:
        emit({"type": "error", "message": f"Deep extract failed: {str(e)[:100]}"})

    return result


# ─── LinkedIn Scraper ─────────────────────────────────────────────────────────


_JS_EXTRACT = open(Path(__file__).parent / "scrapers" / "extract_posts.js").read()  # backend/scrapers/


def extract_all_posts_js(page) -> list[dict]:
    """Use JavaScript to extract all post data in one pass — works with hashed classes."""
    return page.evaluate(_JS_EXTRACT)


def scrape_posts(page, conn, max_posts: int = MAX_POSTS, on_event=None) -> list[dict]:
    """Smart adaptive LinkedIn post scraper.

    Algorithm:
      1. Build queries dynamically from role x domain x action combos (shuffled each run).
      2. For each query, paginate up to N pages deep (&page=1..N) — stops early when
         pages are exhausted or yielding only duplicates.
      3. Adaptive page budget: queries that yield new results get more pages;
         queries that are mostly dups get killed early.
      4. Time-window filter: uses &sortBy=date_posted to focus on recent content.
      5. Global dedup via content hash against both in-memory set and DB.

    on_event: optional callback(event_dict) for live logging.
    """
    def emit(event):
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass

    all_posts = []
    seen_content = set()
    sno = 1
    queries_searched = 0
    deep_extract_count = 0  # Cap deep extracts per session to avoid rate limiting

    # Load all known posts into memory for O(1) dedup — no more per-post SQL queries
    dedup = DedupCache(conn)
    console.print(f"  [dim]Loaded {dedup.size} known posts into dedup cache[/]")
    emit({"type": "cache_loaded", "size": dedup.size})

    # ── Adaptive budget: queries that find new posts earn more pages ──
    # Scale page budget based on target size
    large_run = max_posts >= 500
    BASE_PAGES = 5 if large_run else 3        # pages per query
    BONUS_PAGES = 5 if large_run else 4       # extra pages for productive queries
    DUP_KILL_THRESHOLD = 3 if large_run else 2  # consecutive dup pages before killing query
    STALE_SCROLL_LIMIT = 3 if large_run else 1   # scrolls per page before giving up

    # ── Build fresh query list (shuffled within tiers) ──
    queries = build_smart_queries()

    # ── Track which queries yielded results to avoid re-running in future ──
    query_yield = {}  # query -> new_post_count

    consecutive_timeouts = 0

    for query in queries:
        if len(all_posts) >= max_posts:
            break

        queries_searched += 1
        console.print(f"\n  [cyan]Searching ({queries_searched}/{len(queries)}):[/] {query}")
        emit({"type": "search", "query": query, "index": queries_searched, "total": len(queries)})

        # Adaptive page budget: start with BASE_PAGES, extend if productive
        max_pages = BASE_PAGES
        query_new_total = 0
        consecutive_dup_pages = 0

        for page_num in range(1, BASE_PAGES + BONUS_PAGES + 1):
            if len(all_posts) >= max_posts:
                break
            if page_num > max_pages:
                break  # exceeded adaptive budget

            url = (
                f"https://www.linkedin.com/search/results/content/"
                f"?keywords={quote_plus(query)}"
                f"&sortBy=date_posted"
                f"&page={page_num}"
            )

            emit({"type": "page", "query": query, "page": page_num})
            console.print(f"  [dim]Page {page_num}/{max_pages}[/]")

            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                consecutive_timeouts = 0
            except Exception as e:
                console.print(f"  [red]Navigation failed: {e}[/]")
                emit({"type": "error", "message": f"Navigation failed for '{query}' p{page_num}: {str(e)[:100]}"})
                consecutive_timeouts += 1
                if consecutive_timeouts >= 3:
                    wait = min(30, 10 * consecutive_timeouts)
                    console.print(f"  [yellow]Too many timeouts — cooling down {wait}s[/]")
                    time.sleep(wait)
                break

            time.sleep(random.uniform(3, 6))

            # Scroll through the full page to trigger lazy loading of all posts
            # Use variable scroll amounts and pauses to look human
            for _ in range(random.randint(4, 7)):
                page.evaluate(f"window.scrollBy(0, {random.randint(400, 900)})")
                time.sleep(random.uniform(0.8, 2.0))
            # Scroll back to top so all posts are in DOM
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(random.uniform(0.5, 1.0))

            # Expand ALL truncated posts — click every "see more" / "…more" button
            try:
                see_more_btns = page.query_selector_all(
                    "button[aria-label*='see more'], button[aria-label*='See more'], "
                    "button.see-more-less-button, button[class*='see-more']"
                )
                for btn in see_more_btns:
                    try:
                        btn.scroll_into_view_if_needed()
                        btn.click()
                    except Exception:
                        pass
                if see_more_btns:
                    time.sleep(0.5)  # wait for content to expand
            except Exception:
                pass

            # ── Extract + process posts from this search page ──
            stale_rounds = 0
            consecutive_all_dup_rounds = 0
            page_new_count = 0

            # FAST PRE-SCAN: extract posts and check how many are already in DB
            # before doing any expensive LLM calls. Skip entire page if mostly known.
            raw_posts = extract_all_posts_js(page)
            emit({"type": "extract", "count": len(raw_posts)})

            if raw_posts:
                # Quick scan: count how many posts we already have
                prescan_known = 0
                prescan_total = 0
                for raw in raw_posts:
                    c = raw.get("content", "").strip()
                    if not c or len(c) < 20:
                        continue
                    prescan_total += 1
                    c_key = c[:100].lower()
                    c_h = content_hash(c)
                    p_url = raw.get("postUrl", "")
                    if c_key in seen_content or dedup.exists(p_url, c_h, c):
                        prescan_known += 1

                if prescan_total > 0 and prescan_known / prescan_total >= 0.9:
                    # 90%+ already known — kill entire query immediately
                    pct = int(prescan_known / prescan_total * 100)
                    emit({"type": "page_skip", "known": prescan_known, "total": prescan_total,
                          "message": f"Page {page_num}: {pct}% known — killing query"})
                    console.print(f"  [dim]Page {page_num}: {prescan_known}/{prescan_total} known ({pct}%) — skipping entire query[/]")
                    break  # kill query — deeper pages will be even worse

            while len(all_posts) < max_posts and stale_rounds < STALE_SCROLL_LIMIT:
                new_this_round = 0
                db_dup_count = 0

                for raw in raw_posts:
                    if len(all_posts) >= max_posts:
                        break

                    content = raw.get("content", "").strip()
                    if not content or len(content) < 20:
                        continue

                    content_key = content[:100].lower()
                    if content_key in seen_content:
                        continue
                    seen_content.add(content_key)

                    # Cross-session dedup: O(1) in-memory check instead of SQL
                    c_hash = content_hash(content)
                    post_url = raw.get("postUrl", "")
                    if dedup.exists(post_url, c_hash, content):
                        db_dup_count += 1
                        emit({"type": "dedup", "author": raw.get("authorName", "Unknown")})
                        continue

                    new_this_round += 1

                    # Emails: mailto links + regex + LLM deobfuscation
                    emails = raw.get("emails", "")
                    regex_emails = extract_emails(content)
                    if regex_emails and regex_emails not in emails:
                        emails = ", ".join(filter(None, [emails, regex_emails]))

                    # LLM deobfuscation: catch "hr at company dot com" patterns
                    if not emails:
                        llm_emails = llm_extract_emails(content)
                        if llm_emails:
                            emails = ", ".join(llm_emails)

                    # LLM extraction (role, company, location, experience)
                    emit({"type": "llm", "author": raw.get("authorName", "Unknown"), "content_preview": content[:80]})
                    llm = llm_extract(content)
                    roles      = llm.get("role") or extract_roles(content)
                    location   = llm.get("location") or extract_location(content)
                    experience = llm.get("experience") or extract_experience(content)
                    company    = llm.get("company", "")

                    # Normalize experience from regex fallback too
                    if experience and not any(c.isdigit() for c in experience[:3]):
                        experience = normalize_experience(experience)

                    domain = score_domain_relevance(content)

                    # Fitness check — skip posts that don't match profile
                    fit, reason = is_good_fit(roles, experience)
                    if not fit:
                        console.print(
                            f"  [dim]SKIP {raw.get('authorName', '')[:15]} | "
                            f"{roles[:20]} | {reason}[/]"
                        )
                        emit({"type": "skip", "author": raw.get("authorName", "Unknown"), "reason": f"{roles[:20]} | {reason}"})
                        continue

                    # ── Deep extraction: visit the actual post URL for full content ──
                    author_url = raw.get("authorUrl", "")
                    deep_data = {}
                    full_content = ""
                    if post_url and is_hiring_post(content) and deep_extract_count < 30:
                        emit({"type": "info", "message": f"Deep extracting: {raw.get('authorName', '')[:25]}"})
                        deep_data = deep_extract_post(page, post_url, on_event=on_event)
                        deep_extract_count += 1
                        if deep_data.get("emails") and not emails:
                            emails = deep_data["emails"]
                        full_content = deep_data.get("full_content", "")

                        # Re-run LLM analysis on full content for richer extraction
                        if full_content and len(full_content) > 200:
                            deep_analysis = llm_deep_analyze(full_content)
                            if deep_analysis:
                                roles = deep_analysis.get("role") or roles
                                company = deep_analysis.get("company") or company
                                location = deep_analysis.get("location") or location
                                experience = deep_analysis.get("experience") or experience
                                if deep_analysis.get("emails") and not emails:
                                    emails = deep_analysis["emails"]

                        # Navigate back to search results after deep extract
                        try:
                            page.go_back(timeout=10000)
                            time.sleep(1)
                        except Exception:
                            pass

                    # Profile email: last resort if still no email
                    if not emails and author_url and "/in/" in author_url and is_hiring_post(content):
                        emit({"type": "info", "message": f"Visiting profile for email: {raw.get('authorName', '')[:25]}"})
                        profile_email = extract_profile_email(page, author_url, on_event=on_event)
                        if profile_email:
                            emails = profile_email
                        try:
                            page.go_back(timeout=10000)
                            time.sleep(1)
                        except Exception:
                            pass

                    data = {
                        "sno":             sno,
                        "author_name":     raw.get("authorName") or "Unknown",
                        "author_profile":  author_url,
                        "author_headline": raw.get("headline", ""),
                        "post_url":        raw.get("postUrl", ""),
                        "content":         full_content or content,
                        "full_content":    full_content or None,
                        "role_hiring_for": roles,
                        "company":         company,
                        "email":           emails,
                        "location":        location,
                        "experience":      experience,
                        "domain_relevance":domain,
                        "post_date":       raw.get("postDate", ""),
                        "keyword_matched": query,
                        "is_hiring":       is_hiring_post(content),
                        "deep_extracted":  bool(deep_data.get("full_content")),
                        "apply_url":       deep_data.get("apply_url", ""),
                        "fit_score":       deep_data.get("fit_score") if deep_data else None,
                        "salary":          deep_data.get("salary") if deep_data else None,
                        "tech_stack":      deep_data.get("tech_stack") if deep_data else None,
                        "fit_reasons":     deep_data.get("fit_reasons") if deep_data else None,
                    }

                    all_posts.append(data)
                    dedup.add(post_url, c_hash, content)  # register in cache for same-session dedup
                    sno += 1

                    emit({
                        "type": "found",
                        "sno": data["sno"],
                        "author": data["author_name"],
                        "role": roles,
                        "company": company,
                        "email": emails,
                        "domain": domain,
                        "experience": experience,
                        "is_hiring": data["is_hiring"],
                    })

                    # Color output by domain relevance
                    domain_tag = "[bold green]H[/]" if domain == "High" else "[yellow]M[/]" if domain == "Medium" else "[dim]L[/]"
                    console.print(
                        f"  [bold green]#{data['sno']}[/] "
                        f"{domain_tag} "
                        f"[white]{data['author_name'][:18]}[/] | "
                        f"[cyan]{str(roles)[:18]}[/] | "
                        f"{(experience or '-')[:10]} | "
                        f"Email: [yellow]{(data['email'] or 'none')[:28]}[/]"
                    )

                # Scroll down to load more posts
                if new_this_round == 0:
                    stale_rounds += 1
                else:
                    stale_rounds = 0

                # Early exit: if ALL posts in this batch were DB duplicates
                if db_dup_count > 0 and new_this_round == 0 and db_dup_count >= len(raw_posts) * 0.8:
                    consecutive_all_dup_rounds += 1
                else:
                    consecutive_all_dup_rounds = 0

                if len(all_posts) < max_posts and stale_rounds < STALE_SCROLL_LIMIT:
                    emit({"type": "scroll", "message": f"Scrolling for more posts... ({len(all_posts)} found so far)"})
                    for _ in range(3):
                        page.evaluate("window.scrollBy(0, 1000)")
                        time.sleep(0.3)
                    time.sleep(1)
                    # Re-extract after scrolling for next iteration
                    raw_posts = extract_all_posts_js(page)

            # ── Adaptive decisions for this page ──
            page_new_count += new_this_round

            if consecutive_all_dup_rounds >= DUP_KILL_THRESHOLD:
                console.print(f"  [dim]All dups on page {page_num} — killing query[/]")
                emit({"type": "skip_query", "message": f"Killing '{query}' — consecutive dup pages"})
                break

            # ── Adaptive budget: extend if this page was productive ──
            if page_new_count > 0:
                query_new_total += page_new_count
                consecutive_dup_pages = 0
                # Reward: if this page found 2+ new posts, grant bonus pages
                if page_new_count >= 2 and max_pages < BASE_PAGES + BONUS_PAGES:
                    max_pages = min(max_pages + 2, BASE_PAGES + BONUS_PAGES)
                    console.print(f"  [green]Productive page! Extended budget to {max_pages} pages[/]")
            else:
                consecutive_dup_pages += 1
                if consecutive_dup_pages >= DUP_KILL_THRESHOLD:
                    console.print(f"  [dim]{consecutive_dup_pages} dup pages in a row — moving on[/]")
                    break

            # Delay between pages — longer to avoid rate limits
            if page_num < max_pages and len(all_posts) < max_posts:
                time.sleep(random.uniform(3, 7))

        # ── Log query results ──
        query_yield[query] = query_new_total
        console.print(f"  [dim]Query '{query[:35]}' → {query_new_total} new (total: {len(all_posts)})[/]")
        emit({"type": "query_done", "query": query, "found_count": len(all_posts), "query_new": query_new_total})

        # Longer cooldown between different search queries
        if len(all_posts) < max_posts:
            time.sleep(random.uniform(5, 12))

    return all_posts


# ─── LinkedIn Feed Scraper ────────────────────────────────────────────────────

def scrape_feed(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape LinkedIn's main feed for organic hiring posts.

    The LinkedIn algorithm surfaces hiring posts from your network and beyond.
    This catches posts that search might miss — especially from 2nd/3rd connections.
    """
    def emit(event):
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass

    all_posts = []
    dedup = DedupCache(conn)
    sno = 1
    scroll_count = 0
    dry_streak = 0  # consecutive scrolls with no new posts
    max_scrolls = max(30, max_posts // 2)  # more scrolls — feed has gaps between job posts

    emit({"type": "info", "message": f"Feed scraper: scrolling feed for up to {max_posts} posts ({max_scrolls} scrolls)"})

    try:
        page.goto("https://www.linkedin.com/feed/", timeout=30000, wait_until="domcontentloaded")
        time.sleep(3)
    except Exception as e:
        emit({"type": "error", "message": f"Feed navigation failed: {str(e)[:100]}"})
        return []

    while len(all_posts) < max_posts and scroll_count < max_scrolls:
        scroll_count += 1
        emit({"type": "search", "query": f"Feed scroll #{scroll_count}",
              "index": scroll_count, "total": max_scrolls})

        # Scroll down — variable amount like a real person
        page.evaluate(f"window.scrollBy(0, {random.randint(600, 1200)})")
        time.sleep(random.uniform(3, 6))

        # Click "see more" buttons with small delays between clicks
        try:
            btns = page.query_selector_all(
                "button[aria-label*='see more'], button[aria-label*='See more'], "
                "button.see-more-less-button"
            )
            for btn in btns[:5]:
                try:
                    btn.scroll_into_view_if_needed()
                    time.sleep(random.uniform(0.3, 0.8))
                    btn.click()
                except Exception:
                    pass
            if btns:
                time.sleep(random.uniform(0.8, 1.5))
        except Exception:
            pass

        # Extract posts
        raw_posts = extract_all_posts_js(page)
        emit({"type": "extract", "count": len(raw_posts)})

        new_this_scroll = 0
        for raw in raw_posts:
            if len(all_posts) >= max_posts:
                break

            content = raw.get("content", "").strip()
            if not content or len(content) < 30:
                continue

            # Must be job-related (broader filter for feed posts)
            if not is_feed_job_post(content):
                continue

            c_hash = content_hash(content)
            post_url = raw.get("postUrl", "")
            if dedup.exists(post_url, c_hash, content):
                continue

            # Emails: JS extraction + regex + LLM deobfuscation
            emails = raw.get("emails", "")
            regex_emails = extract_emails(content)
            if regex_emails and regex_emails not in emails:
                emails = ", ".join(filter(None, [emails, regex_emails]))
            if not emails:
                llm_emails = llm_extract_emails(content)
                if llm_emails:
                    emails = ", ".join(llm_emails)

            # LLM extraction
            llm = llm_extract(content)
            roles = llm.get("role") or extract_roles(content)
            location = llm.get("location") or extract_location(content)
            experience = llm.get("experience") or extract_experience(content)
            company = llm.get("company", "")
            domain = score_domain_relevance(content)

            fit, reason = is_good_fit(roles, experience)
            if not fit:
                emit({"type": "skip", "author": raw.get("authorName", "")[:20], "reason": reason})
                continue

            # Profile email: if no email and we have author URL, visit profile
            author_url = raw.get("authorUrl", "")
            if not emails and author_url and "/in/" in author_url:
                emit({"type": "info", "message": f"Visiting profile: {raw.get('authorName', '')[:25]}"})
                profile_email = extract_profile_email(page, author_url, on_event=on_event)
                if profile_email:
                    emails = profile_email

            data = {
                "sno": sno,
                "author_name": raw.get("authorName") or "Unknown",
                "author_profile": author_url,
                "author_headline": raw.get("headline", ""),
                "post_url": post_url,
                "content": content,
                "role_hiring_for": roles,
                "company": company,
                "email": emails,
                "location": location,
                "experience": experience,
                "domain_relevance": domain,
                "post_date": raw.get("postDate", ""),
                "keyword_matched": "feed",
                "is_hiring": True,
            }
            all_posts.append(data)
            dedup.add(post_url, c_hash, content)
            sno += 1
            new_this_scroll += 1

            emit({"type": "found", "sno": sno - 1, "author": data["author_name"][:25],
                  "role": roles[:25], "company": company[:20],
                  "email": (emails or "")[:25], "domain": domain})

        # Track dry streak — stop after 5 consecutive scrolls with no new posts
        if new_this_scroll == 0:
            dry_streak += 1
        else:
            dry_streak = 0
        if dry_streak >= 5 and scroll_count > 8:
            emit({"type": "info", "message": f"Feed: no new posts in {dry_streak} scrolls, stopping"})
            break

    emit({"type": "done", "total": len(all_posts),
          "queries_searched": scroll_count,
          "message": f"Feed scraper done: {len(all_posts)} posts from {scroll_count} scrolls"})
    return all_posts


# ─── LinkedIn Hashtag Scraper ─────────────────────────────────────────────────


def scrape_hashtags(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape LinkedIn hashtag feeds for hiring posts.

    Hashtag feeds like #hiring, #AIjobs, #healthcareAI are goldmines for
    recruiter posts that often include contact emails.
    """
    def emit(event):
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass

    all_posts = []
    dedup = DedupCache(conn)
    sno = 1

    hashtags = list(_HASHTAG_FEEDS)
    random.shuffle(hashtags)

    emit({"type": "info", "message": f"Hashtag scraper: {len(hashtags)} hashtags to browse"})

    for hi, hashtag in enumerate(hashtags):
        if len(all_posts) >= max_posts:
            break

        emit({"type": "search", "query": f"#{hashtag}",
              "index": hi + 1, "total": len(hashtags)})

        try:
            url = f"https://www.linkedin.com/feed/hashtag/{hashtag}/"
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            time.sleep(random.uniform(4, 8))
        except Exception as e:
            emit({"type": "error", "message": f"Hashtag #{hashtag} failed: {str(e)[:80]}"})
            continue

        # Scroll to load posts — human-like variable scrolling
        for _ in range(random.randint(4, 7)):
            page.evaluate(f"window.scrollBy(0, {random.randint(500, 900)})")
            time.sleep(random.uniform(1.5, 3.0))

        # Click see more buttons
        try:
            btns = page.query_selector_all(
                "button[aria-label*='see more'], button[aria-label*='See more']"
            )
            for btn in btns[:8]:
                try:
                    btn.scroll_into_view_if_needed()
                    btn.click()
                except Exception:
                    pass
            if btns:
                time.sleep(0.5)
        except Exception:
            pass

        raw_posts = extract_all_posts_js(page)
        emit({"type": "extract", "count": len(raw_posts)})

        new_this_hashtag = 0
        for raw in raw_posts:
            if len(all_posts) >= max_posts:
                break

            content = raw.get("content", "").strip()
            if not content or len(content) < 30:
                continue

            if not is_hiring_post(content):
                continue

            c_hash = content_hash(content)
            post_url = raw.get("postUrl", "")
            if dedup.exists(post_url, c_hash, content):
                continue

            # Full extraction pipeline
            emails = raw.get("emails", "")
            regex_emails = extract_emails(content)
            if regex_emails and regex_emails not in emails:
                emails = ", ".join(filter(None, [emails, regex_emails]))
            if not emails:
                llm_emails = llm_extract_emails(content)
                if llm_emails:
                    emails = ", ".join(llm_emails)

            llm = llm_extract(content)
            roles = llm.get("role") or extract_roles(content)
            location = llm.get("location") or extract_location(content)
            experience = llm.get("experience") or extract_experience(content)
            company = llm.get("company", "")
            domain = score_domain_relevance(content)

            fit, reason = is_good_fit(roles, experience)
            if not fit:
                emit({"type": "skip", "author": raw.get("authorName", "")[:20], "reason": reason})
                continue

            # Profile email extraction
            author_url = raw.get("authorUrl", "")
            if not emails and author_url and "/in/" in author_url:
                emit({"type": "info", "message": f"Visiting profile: {raw.get('authorName', '')[:25]}"})
                profile_email = extract_profile_email(page, author_url, on_event=on_event)
                if profile_email:
                    emails = profile_email

            data = {
                "sno": sno,
                "author_name": raw.get("authorName") or "Unknown",
                "author_profile": author_url,
                "author_headline": raw.get("headline", ""),
                "post_url": post_url,
                "content": content,
                "role_hiring_for": roles,
                "company": company,
                "email": emails,
                "location": location,
                "experience": experience,
                "domain_relevance": domain,
                "post_date": raw.get("postDate", ""),
                "keyword_matched": f"#{hashtag}",
                "is_hiring": True,
            }
            all_posts.append(data)
            dedup.add(post_url, c_hash, content)
            sno += 1
            new_this_hashtag += 1

            emit({"type": "found", "sno": sno - 1, "author": data["author_name"][:25],
                  "role": roles[:25], "company": company[:20],
                  "email": (emails or "")[:25], "domain": domain})

        emit({"type": "query_done", "query": f"#{hashtag}", "found_count": len(all_posts), "query_new": new_this_hashtag})
        # Longer cooldown between hashtags
        time.sleep(random.uniform(5, 12))

    emit({"type": "done", "total": len(all_posts),
          "queries_searched": len(hashtags),
          "message": f"Hashtag scraper done: {len(all_posts)} posts from {len(hashtags)} hashtags"})
    return all_posts


# ─── Deep Fetch Backfiller ────────────────────────────────────────────────────

def backfill_deep_extract(page, conn, max_visits: int = 100, on_event=None) -> int:
    """Retroactively visit post URLs in DB to extract full content + emails.

    Finds posts that have a post_url but haven't been deep-extracted yet.
    Visits each URL, extracts full content/emails, and updates the DB row.
    Prioritizes hiring posts with High domain relevance.

    Returns count of posts enriched.
    """
    def emit(event):
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass

    rows = conn.execute(
        """SELECT id, post_url, author_name, email, content FROM posts
           WHERE post_url IS NOT NULL AND post_url != ''
             AND deep_extracted = 0
             AND is_hiring = 1
           ORDER BY
             CASE WHEN email IS NULL OR email = '' THEN 0 ELSE 1 END,  -- no-email first
             CASE domain_relevance WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
             created_at DESC
           LIMIT ?""",
        (max_visits,),
    ).fetchall()

    if not rows:
        emit({"type": "info", "message": "No posts to deep-fetch — all already extracted"})
        return 0

    emit({"type": "info", "message": f"Deep fetcher: {len(rows)} post URLs to visit"})

    enriched = 0
    for i, row in enumerate(rows):
        post_id = row["id"]
        post_url = row["post_url"]
        author = row["author_name"] or "Unknown"
        existing_email = row["email"] or ""

        emit({"type": "search", "query": f"Deep: {author[:25]}",
              "index": i + 1, "total": len(rows)})

        deep = deep_extract_post(page, post_url, on_event=on_event)

        updates = {"deep_extracted": 1}
        new_email = ""

        if deep.get("full_content"):
            updates["full_content"] = deep["full_content"]
            # Update main content if it's significantly richer
            existing_content = row["content"] or ""
            if len(deep["full_content"]) > len(existing_content) * 1.3:
                updates["content"] = deep["full_content"]

        if deep.get("emails") and not existing_email:
            new_email = deep["emails"]
            updates["email"] = new_email

        if deep.get("apply_url"):
            updates["apply_url"] = deep["apply_url"]

        # Run deep LLM analysis on full content
        full_text = deep.get("full_content", "") or row["content"] or ""
        if full_text and len(full_text) > 200:
            analysis = llm_deep_analyze(full_text)
            if analysis:
                if analysis.get("fit_score"):
                    updates["fit_score"] = analysis["fit_score"]
                if analysis.get("emails") and not new_email and not existing_email:
                    new_email = analysis["emails"]
                    updates["email"] = new_email

        # Update DB
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [post_id]
        conn.execute(f"UPDATE posts SET {set_clause}, updated_at = datetime('now') WHERE id = ?", values)
        conn.commit()

        if new_email:
            enriched += 1
            emit({"type": "found", "sno": enriched, "author": author[:25],
                  "role": "deep-fetched", "company": "", "email": new_email[:30], "domain": "deep"})
        else:
            emit({"type": "skip", "author": author[:25],
                  "reason": f"No new email (content: {len(deep.get('full_content', ''))} chars)"})

        # Longer delay between post visits to avoid rate limits
        time.sleep(random.uniform(5, 10))

    emit({"type": "done", "total": enriched,
          "queries_searched": len(rows),
          "message": f"Deep fetch done: {enriched}/{len(rows)} posts enriched with emails"})
    return enriched


# ─── Display ─────────────────────────────────────────────────────────────────

def show_results_table(posts: list[dict]):
    table = Table(
        title="Parsed LinkedIn Hiring Posts",
        box=box.ROUNDED,
        border_style="blue",
        show_lines=True,
    )
    table.add_column("#",       style="dim",         width=4)
    table.add_column("Author",  style="bold white",  max_width=20)
    table.add_column("Role",    style="cyan",         max_width=20)
    table.add_column("Exp",     style="magenta",      max_width=12)
    table.add_column("Domain",  style="green",        max_width=8)
    table.add_column("Email",   style="yellow",       max_width=28)
    table.add_column("Hiring?", justify="center",     width=8)

    for p in posts:
        hiring = "[green]YES[/]" if p["is_hiring"] else "[dim]no[/]"
        domain = p.get("domain_relevance", "Low")
        domain_styled = f"[bold green]{domain}[/]" if domain == "High" else domain
        table.add_row(
            str(p["sno"]),
            p["author_name"][:20],
            p["role_hiring_for"][:20],
            (p["experience"] or "-")[:12],
            domain_styled,
            (p["email"] or "-")[:28],
            hiring,
        )

    console.print()
    console.print(table)


# ─── Process raw posts through extraction pipeline ───────────────────────────

def process_raw_posts(raw_posts: list[dict], conn, query: str = "") -> list[dict]:
    """Run LLM extraction, domain scoring, dedup on raw scraped posts.
    Works with output from both Playwright and Crawl4AI scrapers."""
    processed = []
    sno = 1

    for raw in raw_posts:
        content = raw.get("content", "").strip()
        if not content or len(content) < 20:
            continue

        # Cross-session dedup
        c_hash = content_hash(content)
        post_url = raw.get("postUrl", raw.get("post_url", ""))
        if post_exists(conn, post_url, c_hash):
            continue

        # Emails: mailto links + regex
        emails = raw.get("emails", raw.get("email", ""))
        regex_emails = extract_emails(content)
        if regex_emails and regex_emails not in emails:
            emails = ", ".join(filter(None, [emails, regex_emails]))

        # LLM extraction (role, company, location, experience)
        llm = llm_extract(content)
        roles      = llm.get("role") or extract_roles(content)
        location   = llm.get("location") or extract_location(content)
        experience = llm.get("experience") or extract_experience(content)
        company    = llm.get("company", "")

        if experience and not any(c.isdigit() for c in experience[:3]):
            experience = normalize_experience(experience)

        domain = score_domain_relevance(content)

        data = {
            "sno":             sno,
            "author_name":     raw.get("authorName", raw.get("author_name", "")) or "Unknown",
            "author_profile":  raw.get("authorUrl", raw.get("author_profile", "")),
            "author_headline": raw.get("headline", raw.get("author_headline", "")),
            "post_url":        post_url,
            "content":         content,
            "role_hiring_for": roles,
            "company":         company,
            "email":           emails,
            "location":        location,
            "experience":      experience,
            "domain_relevance":domain,
            "post_date":       raw.get("postDate", raw.get("post_date", "")),
            "keyword_matched": query,
            "is_hiring":       is_hiring_post(content),
        }

        processed.append(data)
        sno += 1

        console.print(
            f"  [bold green]#{data['sno']}[/] "
            f"[white]{data['author_name'][:20]}[/] | "
            f"[cyan]{str(roles)[:20]}[/] | "
            f"Email: [yellow]{(data['email'] or 'none')[:30]}[/]"
        )

    return processed


# ─── LinkedIn Job Search Scraper (for volume — 1000+ jobs) ───────────────────

_JS_EXTRACT_JOBS = """
() => {
    const cards = document.querySelectorAll('.job-card-container, .jobs-search-results__list-item, [data-job-id]');
    const jobs = [];
    cards.forEach(card => {
        const titleEl = card.querySelector('.job-card-list__title, .job-card-container__link, a[data-control-name="job_card"]');
        const companyEl = card.querySelector('.job-card-container__primary-description, .artdeco-entity-lockup__subtitle, .job-card-container__company-name');
        const locationEl = card.querySelector('.job-card-container__metadata-item, .artdeco-entity-lockup__caption, .job-card-container__metadata-wrapper');
        const linkEl = card.querySelector('a[href*="/jobs/view/"]');

        const title = titleEl ? titleEl.textContent.trim() : '';
        const company = companyEl ? companyEl.textContent.trim() : '';
        const location = locationEl ? locationEl.textContent.trim() : '';
        const jobUrl = linkEl ? linkEl.href.split('?')[0] : '';
        const jobId = card.getAttribute('data-job-id') || jobUrl.match(/\\/view\\/(\\d+)/)?.[1] || '';

        if (title) {
            jobs.push({ title, company, location, jobUrl, jobId });
        }
    });
    return jobs;
}
"""



def scrape_jobs(page, conn, max_jobs: int = MAX_POSTS) -> list[dict]:
    """Scrape LinkedIn Job Search — proper pagination, gets 1000+ jobs."""
    all_jobs = []
    seen_ids = set()
    sno = 1

    for query in JOB_SEARCH_QUERIES:
        if len(all_jobs) >= max_jobs:
            break

        console.print(f"\n  [cyan]Job search:[/] {query}")

        # Paginate through results (25 per page)
        for start in range(0, 200, 25):  # Up to 200 results per query
            if len(all_jobs) >= max_jobs:
                break

            url = (
                f"https://www.linkedin.com/jobs/search/"
                f"?keywords={quote_plus(query)}"
                f"&f_E={JOB_EXP_LEVELS}"
                f"&f_JT={JOB_TYPE}"
                f"&sortBy=DD"  # Date posted (most recent)
                f"&start={start}"
            )

            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                console.print(f"  [red]Navigation failed: {e}[/]")
                break

            time.sleep(2)

            # Scroll to load all job cards
            for _ in range(3):
                page.evaluate("window.scrollBy(0, 600)")
                time.sleep(0.3)
            time.sleep(1)

            # Extract job cards
            raw_jobs = page.evaluate(_JS_EXTRACT_JOBS)
            new_this_page = 0

            for job in raw_jobs:
                if len(all_jobs) >= max_jobs:
                    break

                job_id = job.get("jobId", "")
                title = job.get("title", "").strip()
                if not title or job_id in seen_ids:
                    continue
                if job_id:
                    seen_ids.add(job_id)

                # Role fitness check on the title itself
                fit, reason = is_good_fit(title, "")
                if not fit:
                    console.print(f"  [dim]SKIP {title[:30]} | {reason}[/]")
                    continue

                company = job.get("company", "").strip()
                location = job.get("location", "").strip()
                job_url = job.get("jobUrl", "")

                # Domain score from title + company
                domain = score_domain_relevance(f"{title} {company} {location}")

                content = f"{title} at {company}\n{location}"

                # Dedup against DB
                c_hash = content_hash(content)
                if post_exists(conn, job_url, c_hash):
                    continue

                data = {
                    "sno":             sno,
                    "author_name":     company,
                    "author_profile":  "",
                    "author_headline": "",
                    "post_url":        job_url,
                    "content":         content,
                    "role_hiring_for": title,
                    "company":         company,
                    "email":           "",
                    "location":        location,
                    "experience":      "",
                    "domain_relevance": domain,
                    "post_date":       "",
                    "keyword_matched": query,
                    "is_hiring":       True,
                }

                all_jobs.append(data)
                sno += 1
                new_this_page += 1

                domain_tag = "[bold green]H[/]" if domain == "High" else "[yellow]M[/]" if domain == "Medium" else "[dim]L[/]"
                console.print(
                    f"  [bold green]#{sno-1}[/] "
                    f"{domain_tag} "
                    f"[white]{company[:18]}[/] | "
                    f"[cyan]{title[:22]}[/] | "
                    f"{(location or '-')[:15]}"
                )

            # No new jobs on this page = no more results for this query
            if new_this_page == 0:
                break

            time.sleep(random.uniform(1, 2))

    return all_jobs


# ─── Main ─────────────────────────────────────────────────────────────────────

def _show_summary(posts, conn):
    """Display results table and DB stats."""
    if not posts:
        console.print("\n[red]No posts collected. Check if LinkedIn selectors have changed.[/]")
        conn.close()
        return

    show_results_table(posts)

    inserted, skipped = insert_posts(conn, posts)

    stats = get_stats(conn)
    console.print()
    console.print(f"  [bold]This session:[/]")
    console.print(f"    New posts saved:    [bold green]{inserted}[/]")
    console.print(f"    Duplicates skipped: [dim]{skipped}[/]")
    console.print(f"  [bold]Database totals:[/]")
    console.print(f"    Total posts:        [bold]{stats['total_posts']}[/]")
    console.print(f"    With email:         [bold yellow]{stats['with_email']}[/]")
    console.print(f"    Confirmed hiring:   [bold green]{stats['hiring']}[/]")
    console.print(f"    Domain High:        [bold cyan]{stats['domain'].get('High', 0)}[/]")
    console.print(f"  [bold]DB file:[/]           [cyan]linkedin_jobs.db[/]")
    console.print()
    console.print("  [dim]Export to Excel anytime:  python db.py --export jobs.xlsx[/]")
    console.print("  [dim]Query by role:            python db.py --role 'AI Engineer' --has-email[/]")
    console.print("  [dim]See all stats:            python db.py --stats[/]")
    console.print()

    conn.close()


def _launch_browser():
    """Launch Playwright browser with persistent session, return (playwright, context, page)."""
    session_dir = Path("data/browser_profiles/session")
    p = sync_playwright().start()
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(session_dir),
        headless=False,
        slow_mo=100,
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-gpu",
            "--disable-software-rasterizer",
        ],
    )
    page = context.new_page()

    try:
        from playwright_stealth import stealth_sync
        stealth_sync(page)
    except ImportError:
        pass

    # Check login
    console.print("  [dim]Checking LinkedIn session...[/]")
    page.goto("https://www.linkedin.com/feed", timeout=60000, wait_until="domcontentloaded")
    time.sleep(2)

    if "login" in page.url or "uas" in page.url:
        console.print(Panel(
            "[bold yellow]Not logged in to LinkedIn.[/]\n"
            "Please log in in the browser window, then press Enter here.",
            border_style="yellow",
        ))
        input("  Press Enter after logging in...")
        time.sleep(2)
    else:
        console.print("  [green]LinkedIn session active.[/]")

    return p, context, page


def main():
    import argparse
    parser = argparse.ArgumentParser(description="LinkedIn Hiring Post/Job Parser")
    parser.add_argument("--jobs", action="store_true",
                        help="Scrape LinkedIn Job Search (proper pagination, 1000+ jobs)")
    parser.add_argument("--posts", action="store_true",
                        help="Scrape LinkedIn Posts/Content search (default)")
    parser.add_argument("--both", action="store_true",
                        help="Scrape both Jobs + Posts")
    parser.add_argument("--max", type=int, default=MAX_POSTS,
                        help=f"Max jobs/posts to collect (default: {MAX_POSTS})")
    args = parser.parse_args()

    mode = "jobs" if args.jobs else "both" if args.both else "posts"
    target = args.max

    console.print(Panel.fit(
        "[bold cyan]LinkedIn Job Parser[/]\n"
        f"[dim]Mode: {mode} | Target: {target} | Healthcare AI focus → SQLite DB[/]",
        border_style="cyan",
        box=box.DOUBLE,
    ))
    console.print()

    conn = init_db()
    p, context, page = _launch_browser()

    all_results = []

    if mode in ("jobs", "both"):
        console.print(f"\n  [bold]Scraping LinkedIn Jobs (target: {target})...[/]")
        jobs = scrape_jobs(page, conn, target)
        all_results.extend(jobs)
        console.print(f"\n  [green]Jobs collected: {len(jobs)}[/]")

    remaining = target - len(all_results)
    if mode in ("posts", "both") and remaining > 0:
        console.print(f"\n  [bold]Scraping LinkedIn Posts (target: {remaining})...[/]")
        posts = scrape_posts(page, conn, remaining)
        all_results.extend(posts)
        console.print(f"\n  [green]Posts collected: {len(posts)}[/]")

    context.close()
    p.stop()

    _show_summary(all_results, conn)


if __name__ == "__main__":
    main()
