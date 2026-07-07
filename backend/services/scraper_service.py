"""Scraper service — all scraper-related state, callbacks, and runner functions.

Extracted from server.py for modularity. All original logic is preserved.
Thread safety: reads/writes to scraper_state are protected by _scraper_lock
where appropriate (especially in _make_source_callback and _scraper_coordinator).
"""

import os
import random
import threading
import time

from db import init_db
from services.browser_service import browser_state, _run_on_browser_thread

# ───────────────────────────────────────────────
# Scraper state + lock
# ───────────────────────────────────────────────

scraper_state = {
    "running": False,       # computed: True if any source is active
    "status": "idle",       # idle | running | done | error
    "started_at": None,
    "sources": {},          # per-source state: { "linkedin": { status, log, progress }, ... }
    "active_sources": set(),  # sources currently being scraped (for overlap detection)
}

_scraper_lock = threading.Lock()

# Limit concurrent browser scrapers to avoid resource exhaustion
_browser_semaphore = threading.Semaphore(3)


def _init_source_state():
    """Create a fresh per-source state dict."""
    return {
        "status": "waiting",  # waiting | running | done | error
        "log": [],
        "progress": {"current_query": "", "query_index": 0, "total_queries": 0, "posts_found": 0},
    }


def _make_source_callback(source_name):
    """Create a per-source event callback that stores events to that source's log."""
    def callback(event):
        import datetime as _dt
        event["timestamp"] = _dt.datetime.now().isoformat()
        event["source_id"] = source_name

        with _scraper_lock:
            state = scraper_state["sources"].get(source_name)
            if not state:
                return
            state["log"].append(event)
            # Keep last 300 entries per source
            if len(state["log"]) > 300:
                state["log"] = state["log"][-300:]
            # Update progress
            if event.get("type") == "search":
                state["progress"]["current_query"] = event.get("query", "")
                state["progress"]["query_index"] = event.get("index", 0)
                state["progress"]["total_queries"] = event.get("total", 0)
            if event.get("type") == "found":
                state["progress"]["posts_found"] = event.get("sno", 0)
    return callback


def _run_linkedin_scraper(max_posts, on_event):
    """Run LinkedIn scraper on the browser thread (needs logged-in page)."""
    from post_parser import scrape_posts
    from db import insert_posts as _insert_posts

    with _scraper_lock:
        state = scraper_state["sources"]["linkedin"]
        state["status"] = "running"
    on_event({"type": "info", "message": "Starting LinkedIn scraper..."})

    page = browser_state.get("page")
    if not page:
        on_event({"type": "error", "message": "Browser not running. Start browser first."})
        with _scraper_lock:
            scraper_state["sources"]["linkedin"]["status"] = "error"
        return

    conn = None
    try:
        conn = init_db()
        posts = scrape_posts(page, conn, max_posts=max_posts, on_event=on_event)
        if posts:
            inserted, skipped = _insert_posts(conn, posts)
            on_event({"type": "saved", "count": len(posts), "inserted": inserted, "skipped": skipped,
                       "message": f"LinkedIn: {inserted} new, {skipped} duplicates"})
        total = len(posts) if posts else 0
        with _scraper_lock:
            state = scraper_state["sources"]["linkedin"]
        on_event({"type": "done", "total": total,
                   "queries_searched": state["progress"]["query_index"],
                   "message": f"LinkedIn complete: {total} posts collected"})
        with _scraper_lock:
            scraper_state["sources"]["linkedin"]["status"] = "done"
    except Exception as e:
        on_event({"type": "error", "message": str(e)[:300]})
        with _scraper_lock:
            scraper_state["sources"]["linkedin"]["status"] = "error"
    finally:
        if conn:
            conn.close()


def _run_api_scraper(source_name, scraper_fn, max_posts, on_event):
    """Run an API-based scraper — no browser needed, just HTTP calls."""
    from db import insert_posts as _insert_posts

    with _scraper_lock:
        state = scraper_state["sources"][source_name]
        state["status"] = "running"
    on_event({"type": "info", "message": f"Starting {source_name} API scraper..."})

    conn = None
    try:
        conn = init_db()
        posts = scraper_fn(None, conn, max_posts=max_posts, on_event=on_event)
        if posts:
            inserted, skipped = _insert_posts(conn, posts)
            on_event({"type": "saved", "count": len(posts), "inserted": inserted, "skipped": skipped,
                       "message": f"{source_name}: {inserted} new, {skipped} duplicates"})
        total = len(posts) if posts else 0
        with _scraper_lock:
            state = scraper_state["sources"][source_name]
        on_event({"type": "done", "total": total,
                   "queries_searched": state["progress"]["query_index"],
                   "message": f"{source_name} complete: {total} posts collected"})
        with _scraper_lock:
            scraper_state["sources"][source_name]["status"] = "done"
    except Exception as e:
        on_event({"type": "error", "message": str(e)[:300]})
        with _scraper_lock:
            scraper_state["sources"][source_name]["status"] = "error"
    finally:
        if conn:
            conn.close()


def _run_web_scraper(source_name, scraper_fn, max_posts, on_event):
    """Run a web scraper in its own thread with its own Playwright browser.

    Uses headed mode with anti-detection (same as main browser) because
    headless Chromium gets blocked by DuckDuckGo, Wellfound, and YC.
    Acquires _browser_semaphore to limit concurrent browser instances.
    """
    from playwright.sync_api import sync_playwright
    from db import insert_posts as _insert_posts

    with _scraper_lock:
        state = scraper_state["sources"][source_name]
        state["status"] = "running"
    on_event({"type": "info", "message": f"Starting {source_name} scraper (waiting for browser slot)..."})

    _browser_semaphore.acquire()
    pw = None
    browser = None
    conn = None
    try:
        on_event({"type": "info", "message": f"Starting {source_name} scraper (launching browser)..."})
        conn = init_db()
        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ],
        )
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        # Anti-detection scripts (match main browser)
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)

        posts = scraper_fn(page, conn, max_posts=max_posts, on_event=on_event)
        if posts:
            inserted, skipped = _insert_posts(conn, posts)
            on_event({"type": "saved", "count": len(posts), "inserted": inserted, "skipped": skipped,
                       "message": f"{source_name}: {inserted} new, {skipped} duplicates"})
        total = len(posts) if posts else 0
        with _scraper_lock:
            state = scraper_state["sources"][source_name]
        on_event({"type": "done", "total": total,
                   "queries_searched": state["progress"]["query_index"],
                   "message": f"{source_name} complete: {total} posts collected"})
        with _scraper_lock:
            scraper_state["sources"][source_name]["status"] = "done"
    except Exception as e:
        on_event({"type": "error", "message": str(e)[:300]})
        with _scraper_lock:
            scraper_state["sources"][source_name]["status"] = "error"
    finally:
        _browser_semaphore.release()
        if conn:
            conn.close()
        try:
            if browser:
                browser.close()
            if pw:
                pw.stop()
        except Exception:
            pass


def _run_linkedin_feed_scraper(max_posts, on_event):
    """Run LinkedIn feed scraper on the browser thread."""
    from post_parser import scrape_feed
    from db import insert_posts as _insert_posts

    with _scraper_lock:
        state = scraper_state["sources"]["feed"]
        state["status"] = "running"

    page = browser_state.get("page")
    if not page:
        on_event({"type": "error", "message": "Browser not running."})
        with _scraper_lock:
            scraper_state["sources"]["feed"]["status"] = "error"
        return

    conn = None
    try:
        conn = init_db()
        posts = scrape_feed(page, conn, max_posts=max_posts, on_event=on_event)
        if posts:
            inserted, skipped = _insert_posts(conn, posts)
            on_event({"type": "saved", "count": len(posts), "inserted": inserted, "skipped": skipped,
                       "message": f"Feed: {inserted} new, {skipped} duplicates"})
        with _scraper_lock:
            scraper_state["sources"]["feed"]["status"] = "done"
    except Exception as e:
        on_event({"type": "error", "message": str(e)[:300]})
        with _scraper_lock:
            scraper_state["sources"]["feed"]["status"] = "error"
    finally:
        if conn:
            conn.close()


def _run_linkedin_hashtag_scraper(max_posts, on_event):
    """Run LinkedIn hashtag scraper on the browser thread."""
    from post_parser import scrape_hashtags
    from db import insert_posts as _insert_posts

    with _scraper_lock:
        state = scraper_state["sources"]["hashtags"]
        state["status"] = "running"

    page = browser_state.get("page")
    if not page:
        on_event({"type": "error", "message": "Browser not running."})
        with _scraper_lock:
            scraper_state["sources"]["hashtags"]["status"] = "error"
        return

    conn = None
    try:
        conn = init_db()
        posts = scrape_hashtags(page, conn, max_posts=max_posts, on_event=on_event)
        if posts:
            inserted, skipped = _insert_posts(conn, posts)
            on_event({"type": "saved", "count": len(posts), "inserted": inserted, "skipped": skipped,
                       "message": f"Hashtags: {inserted} new, {skipped} duplicates"})
        with _scraper_lock:
            scraper_state["sources"]["hashtags"]["status"] = "done"
    except Exception as e:
        on_event({"type": "error", "message": str(e)[:300]})
        with _scraper_lock:
            scraper_state["sources"]["hashtags"]["status"] = "error"
    finally:
        if conn:
            conn.close()


def _run_enricher(max_visits, on_event):
    """Run email enricher on the browser thread — visits profiles to fill missing emails."""
    from post_parser import enrich_posts_with_profile_emails

    with _scraper_lock:
        state = scraper_state["sources"]["enricher"]
        state["status"] = "running"
    on_event({"type": "info", "message": "Starting email enricher — visiting profiles for missing emails..."})

    page = browser_state.get("page")
    if not page:
        on_event({"type": "error", "message": "Browser not running."})
        with _scraper_lock:
            scraper_state["sources"]["enricher"]["status"] = "error"
        return

    conn = None
    try:
        conn = init_db()
        enriched = enrich_posts_with_profile_emails(page, conn, max_visits=max_visits, on_event=on_event)
        on_event({"type": "saved", "count": enriched, "inserted": enriched, "skipped": 0,
                   "message": f"Enriched {enriched} posts with profile emails"})
        with _scraper_lock:
            scraper_state["sources"]["enricher"]["status"] = "done"
    except Exception as e:
        on_event({"type": "error", "message": str(e)[:300]})
        with _scraper_lock:
            scraper_state["sources"]["enricher"]["status"] = "error"
    finally:
        if conn:
            conn.close()


def _run_deep_fetcher(max_visits, on_event):
    """Run deep fetcher on the browser thread — visits post URLs to extract full content + emails."""
    from post_parser import backfill_deep_extract

    with _scraper_lock:
        state = scraper_state["sources"]["deepfetch"]
        state["status"] = "running"
    on_event({"type": "info", "message": "Starting deep fetcher — visiting post URLs for full content..."})

    page = browser_state.get("page")
    if not page:
        on_event({"type": "error", "message": "Browser not running."})
        with _scraper_lock:
            scraper_state["sources"]["deepfetch"]["status"] = "error"
        return

    conn = None
    try:
        conn = init_db()
        enriched = backfill_deep_extract(page, conn, max_visits=max_visits, on_event=on_event)
        on_event({"type": "saved", "count": enriched, "inserted": enriched, "skipped": 0,
                   "message": f"Deep fetched {enriched} posts with new emails"})
        with _scraper_lock:
            scraper_state["sources"]["deepfetch"]["status"] = "done"
    except Exception as e:
        on_event({"type": "error", "message": str(e)[:300]})
        with _scraper_lock:
            scraper_state["sources"]["deepfetch"]["status"] = "error"
    finally:
        if conn:
            conn.close()


def _run_career_link_scraper(source_name, max_visits, on_event):
    """Run career link follower in its own browser — follows external links for emails.
    Acquires _browser_semaphore to limit concurrent browser instances.
    """
    from playwright.sync_api import sync_playwright
    from scrapers.web_scrapers import follow_career_links

    with _scraper_lock:
        state = scraper_state["sources"][source_name]
        state["status"] = "running"
    on_event({"type": "info", "message": "Starting career link follower (waiting for browser slot)..."})

    _browser_semaphore.acquire()
    pw = None
    browser = None
    conn = None
    try:
        on_event({"type": "info", "message": "Starting career link follower..."})
        conn = init_db()
        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--disable-infobars"],
        )
        page = browser.new_page(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        enriched = follow_career_links(page, conn, max_visits=max_visits, on_event=on_event)
        on_event({"type": "saved", "count": enriched, "inserted": enriched, "skipped": 0,
                   "message": f"Career links: {enriched} posts enriched"})
        with _scraper_lock:
            scraper_state["sources"][source_name]["status"] = "done"
    except Exception as e:
        on_event({"type": "error", "message": str(e)[:300]})
        with _scraper_lock:
            scraper_state["sources"][source_name]["status"] = "error"
    finally:
        _browser_semaphore.release()
        if conn:
            conn.close()
        try:
            if browser:
                browser.close()
            if pw:
                pw.stop()
        except Exception:
            pass


def _scraper_coordinator(max_posts: int, sources: list[str], user_id=None):
    """Coordinator thread: launches all source scrapers in parallel where possible.

    LinkedIn-based sources (search, feed, hashtags, enricher, deepfetch) run SEQUENTIALLY on
    the browser thread (Playwright single-thread constraint).
    Web scrapers (google, wellfound, yc) run in PARALLEL with their own browsers.

    `user_id` is the user who started the scrape; all scraped rows must land in
    that user's DB. We set the context var on this coordinator thread and wrap
    every child thread target with run_with_user (context vars don't propagate
    into new threads).
    """
    import datetime as _dt
    from scrapers.web_scrapers import scrape_google, scrape_wellfound as scrape_wellfound_web, scrape_yc_jobs
    from db import current_user_id
    from worker_ctx import run_with_user

    current_user_id.set(user_id)

    with _scraper_lock:
        scraper_state["running"] = True
        scraper_state["status"] = "running"
        if not scraper_state.get("started_at"):
            scraper_state["started_at"] = _dt.datetime.now().isoformat()

        # Initialize per-source state (don't wipe existing sources from other coordinators)
        for source in sources:
            scraper_state["sources"][source] = _init_source_state()
            scraper_state["active_sources"].add(source)

    try:
        # Compute per-source budgets
        per_source = max(50, max_posts // len(sources)) if len(sources) > 1 else max_posts

        # Create a shared DedupCache for cross-scraper deduplication (thread-safe)
        from db import DedupCache
        _shared_conn = init_db()
        shared_dedup = DedupCache(_shared_conn)
        _shared_conn.close()

        threads = []

        # ── LinkedIn-based sources: must all run on browser thread (sequentially) ──
        linkedin_sources = [s for s in sources if s in ("linkedin", "feed", "hashtags", "enricher", "deepfetch")]
        if linkedin_sources:
            def _browser_sources_runner():
                """Run all LinkedIn-based sources sequentially on the browser thread."""
                for src in linkedin_sources:
                    with _scraper_lock:
                        still_running = scraper_state["running"]
                    if not still_running:
                        break
                    on_event = _make_source_callback(src)
                    budget = per_source

                    if src == "linkedin":
                        _run_linkedin_scraper(budget, on_event)
                    elif src == "feed":
                        _run_linkedin_feed_scraper(budget, on_event)
                    elif src == "hashtags":
                        _run_linkedin_hashtag_scraper(budget, on_event)
                    elif src == "enricher":
                        _run_enricher(min(budget, 150), on_event)
                    elif src == "deepfetch":
                        _run_deep_fetcher(min(budget, 100), on_event)

            def _browser_thread():
                _run_on_browser_thread(_browser_sources_runner, timeout=14400)

            t = threading.Thread(target=run_with_user(user_id, _browser_thread), daemon=True)
            threads.append(t)
            t.start()

        # ── API scrapers: no browser needed, lightweight HTTP calls ──
        from scrapers.api_scrapers import (
            scrape_remoteok, scrape_himalayas, scrape_hn_hiring,
            scrape_remotive, scrape_wwr_rss, scrape_workingnomads,
            scrape_greenhouse, scrape_lever, scrape_ashby, scrape_jobspy,
        )

        api_source_map = {
            "remoteok": scrape_remoteok,
            "himalayas": scrape_himalayas,
            "hn": scrape_hn_hiring,
            "remotive": scrape_remotive,
            "wwr_rss": scrape_wwr_rss,
            "workingnomads": scrape_workingnomads,
            "greenhouse": scrape_greenhouse,
            "lever": scrape_lever,
            "ashby": scrape_ashby,
            "jobspy": scrape_jobspy,
        }

        for source in sources:
            if source in linkedin_sources or source == "career_links":
                continue
            if source in api_source_map:
                on_event = _make_source_callback(source)
                budget = min(per_source, max_posts)
                scraper_fn = api_source_map[source]
                t = threading.Thread(
                    target=run_with_user(user_id, _run_api_scraper, source, scraper_fn, budget, on_event),
                    daemon=True,
                )
                threads.append(t)
                t.start()

        # ── Generic scrapers (HTML + API, config-driven, no browser) ──
        from scrapers.generic_scrapers import scrape_generic_html, scrape_generic_api
        from config_sources import GENERIC_HTML_SOURCES, GENERIC_API_SOURCES

        for source in sources:
            if source in linkedin_sources or source == "career_links":
                continue
            if source in api_source_map:
                continue  # Already handled above
            if source in GENERIC_HTML_SOURCES:
                on_event = _make_source_callback(source)
                budget = min(per_source, max_posts)
                t = threading.Thread(
                    target=run_with_user(user_id, _run_api_scraper, source, lambda p, c, max_posts=budget, on_event=on_event, sk=source: scrape_generic_html(sk, p, c, max_posts, on_event), budget, on_event),
                    daemon=True,
                )
                threads.append(t)
                t.start()
                continue
            if source in GENERIC_API_SOURCES:
                on_event = _make_source_callback(source)
                budget = min(per_source, max_posts)
                t = threading.Thread(
                    target=run_with_user(user_id, _run_api_scraper, source, lambda p, c, max_posts=budget, on_event=on_event, sk=source: scrape_generic_api(sk, p, c, max_posts, on_event), budget, on_event),
                    daemon=True,
                )
                threads.append(t)
                t.start()
                continue

        # ── Web scrapers: each gets its own browser in its own thread (parallel) ──
        from scrapers.web_scrapers import (
            scrape_indeed, scrape_naukri, scrape_arcdev,
            scrape_weworkremotely, scrape_japandev,
            scrape_euremotejobs, scrape_bayt, scrape_remoteai,
        )

        web_source_map = {
            "google": scrape_google,
            "wellfound": scrape_wellfound_web,
            "yc": scrape_yc_jobs,
            "indeed": scrape_indeed,
            "naukri": scrape_naukri,
            "arcdev": scrape_arcdev,
            "weworkremotely": scrape_weworkremotely,
            "japandev": scrape_japandev,
            "euremotejobs": scrape_euremotejobs,
            "bayt": scrape_bayt,
            "remoteai": scrape_remoteai,
        }

        for source in sources:
            if source in linkedin_sources or source in api_source_map:
                continue
            if source == "career_links":
                # Career link follower: own browser, parallel thread
                on_event = _make_source_callback(source)
                budget = min(per_source, 50)
                t = threading.Thread(
                    target=run_with_user(user_id, _run_career_link_scraper, source, budget, on_event),
                    daemon=True,
                )
                threads.append(t)
                t.start()
                continue
            if source not in web_source_map:
                continue
            on_event = _make_source_callback(source)
            budget = min(per_source, max_posts)
            scraper_fn = web_source_map[source]
            t = threading.Thread(
                target=run_with_user(user_id, _run_web_scraper, source, scraper_fn, budget, on_event),
                daemon=True,
            )
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()
    finally:
        # Remove this coordinator's sources from active set
        with _scraper_lock:
            for source in sources:
                scraper_state["active_sources"].discard(source)
            # Only set running=False if no other coordinator is still active
            if not scraper_state["active_sources"]:
                # Only evaluate sources from this coordinator run
                coordinator_sources = {s: scraper_state["sources"].get(s) for s in sources}
                scraper_state["status"] = "error" if all(
                    s["status"] == "error" for s in coordinator_sources.values() if s
                ) else "done"
                scraper_state["running"] = False
                scraper_state["started_at"] = None
