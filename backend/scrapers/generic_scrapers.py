"""
Generic Scraper Engine
-----------------------
Config-driven scrapers for HTML and API sources.
One engine handles all sites defined in config_sources.py.

Usage:
    from scrapers.generic_scrapers import scrape_generic_html, scrape_generic_api
    posts = scrape_generic_html("remoteco", page=None, conn=conn, max_posts=50, on_event=cb)
"""

import re
import time
import random
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from db import content_hash, DedupCache
from config_sources import GENERIC_HTML_SOURCES, GENERIC_API_SOURCES
from scrapers.api_scrapers import _process_api_job, _make_emit, _is_fresh, _API_HEADERS


def scrape_generic_html(source_key: str, page, conn, max_posts: int = 50, on_event=None) -> list[dict]:
    """Generic HTML scraper — uses requests + BeautifulSoup (no browser needed).
    Reads config from GENERIC_HTML_SOURCES[source_key].
    """
    config = GENERIC_HTML_SOURCES.get(source_key)
    if not config:
        return []

    all_posts = []
    dedup = DedupCache(conn)
    emit = _make_emit(on_event)
    label = config["label"]
    base_url = config.get("base_url", "")
    sel = config["selectors"]

    urls = config.get("urls", [])
    emit({"type": "info", "message": f"Starting {label} scraper ({len(urls)} pages)..."})

    for si, url in enumerate(urls):
        if len(all_posts) >= max_posts:
            break

        emit({"type": "search", "query": f"{label}: page {si + 1}", "index": si + 1, "total": len(urls)})

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            }
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                emit({"type": "error", "message": f"{label}: HTTP {resp.status_code}"})
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            emit({"type": "error", "message": f"{label}: {str(e)[:150]}"})
            continue

        # Find job cards
        cards = soup.select(sel["card"])
        emit({"type": "extract", "count": len(cards)})

        for card in cards:
            if len(all_posts) >= max_posts:
                break

            # Extract title
            title_el = card.select_one(sel.get("title", "h2 a"))
            title = title_el.get_text(strip=True) if title_el else ""
            if not title or len(title) < 5:
                continue

            # Extract link
            link_el = card.select_one(sel.get("link", "a[href]"))
            href = ""
            if link_el and link_el.get("href"):
                href = link_el["href"]
                if href.startswith("/"):
                    href = urljoin(base_url, href)

            if not href:
                continue

            # Extract company
            company_el = card.select_one(sel.get("company", ".company"))
            company = company_el.get_text(strip=True) if company_el else ""

            # Extract location
            loc_el = card.select_one(sel.get("location", ".location"))
            location = loc_el.get_text(strip=True) if loc_el else "Remote"

            # Build description from card text
            card_text = card.get_text(separator=" ", strip=True)[:300]

            _process_api_job(
                href, title, company, location, card_text,
                label, source_key, dedup, all_posts, emit,
            )

        time.sleep(random.uniform(1, 3))

    emit({"type": "done", "total": len(all_posts), "queries_searched": len(urls),
          "message": f"{label} complete: {len(all_posts)} posts"})
    return all_posts


def scrape_generic_api(source_key: str, page, conn, max_posts: int = 50, on_event=None) -> list[dict]:
    """Generic API scraper — hits JSON endpoints defined in config.
    Reads config from GENERIC_API_SOURCES[source_key].
    """
    config = GENERIC_API_SOURCES.get(source_key)
    if not config:
        return []

    all_posts = []
    dedup = DedupCache(conn)
    emit = _make_emit(on_event)
    label = config["label"]
    fields = config["fields"]
    search_terms = config.get("search_terms", ["AI Engineer"])

    emit({"type": "info", "message": f"Starting {label} API scraper..."})

    # Handle company-based APIs (SmartRecruiters style)
    companies = config.get("companies")
    if companies:
        url_template = config.get("url_template", "")
        for ci, company in enumerate(companies):
            if len(all_posts) >= max_posts:
                break
            for term in search_terms:
                if len(all_posts) >= max_posts:
                    break
                url = url_template.format(company=company, query=term)
                emit({"type": "search", "query": f"{label}: {company}/{term}", "index": ci + 1, "total": len(companies)})
                _fetch_api_jobs(url, config, label, f"{company}/{term}", dedup, all_posts, emit, max_posts)
                time.sleep(random.uniform(0.3, 0.8))
        emit({"type": "done", "total": len(all_posts), "queries_searched": len(companies),
              "message": f"{label} complete: {len(all_posts)} posts"})
        return all_posts

    # Handle search-based APIs
    url_template = config.get("url", "")
    for si, term in enumerate(search_terms):
        if len(all_posts) >= max_posts:
            break
        url = url_template.format(query=term)
        emit({"type": "search", "query": f"{label}: {term}", "index": si + 1, "total": len(search_terms)})
        _fetch_api_jobs(url, config, label, term, dedup, all_posts, emit, max_posts)
        time.sleep(random.uniform(0.5, 1.5))

    emit({"type": "done", "total": len(all_posts), "queries_searched": len(search_terms),
          "message": f"{label} complete: {len(all_posts)} posts"})
    return all_posts


def _fetch_api_jobs(url, config, label, term, dedup, all_posts, emit, max_posts):
    """Fetch and process jobs from a single API endpoint."""
    fields = config["fields"]
    jobs_path = config.get("jobs_path", "")
    extra_headers = config.get("headers", {})

    try:
        headers = {**_API_HEADERS, **extra_headers}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            emit({"type": "error", "message": f"{label}: HTTP {resp.status_code}"})
            return
        data = resp.json()
    except Exception as e:
        emit({"type": "error", "message": f"{label}: {str(e)[:150]}"})
        return

    # Navigate to jobs list using dot-path
    jobs = data
    if jobs_path:
        for key in jobs_path.split("."):
            if isinstance(jobs, dict):
                jobs = jobs.get(key, [])
            else:
                break

    if not isinstance(jobs, list):
        return

    emit({"type": "extract", "count": len(jobs)})

    for job in jobs:
        if len(all_posts) >= max_posts:
            break

        title = _get_nested(job, fields.get("title", "title"))
        company = _get_nested(job, fields.get("company", "company"))
        location = _get_nested(job, fields.get("location", "location")) or "Remote"
        job_url = _get_nested(job, fields.get("url", "url"))
        date_str = _get_nested(job, fields.get("date", ""))

        if not title or not job_url:
            continue

        if date_str and not _is_fresh(date_str):
            continue

        _process_api_job(
            str(job_url), str(title), str(company), str(location), "",
            label, term, dedup, all_posts, emit,
        )


def _get_nested(obj: dict, path: str):
    """Get a value from a nested dict using dot notation: 'a.b.c' -> obj['a']['b']['c']"""
    if not path:
        return ""
    for key in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(key, "")
        else:
            return ""
    return obj or ""
