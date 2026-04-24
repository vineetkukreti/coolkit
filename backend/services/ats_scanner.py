"""
ATS Portal Scanner — Python port of career-ops/scan.mjs

Fetches Greenhouse, Ashby, and Lever APIs directly, applies title
filters from portals.yml, deduplicates against the SQLite DB,
and returns normalized job dicts ready for insert_posts().

Usage:
    from ats_scanner import scan_all
    from db import init_db

    conn = init_db()
    new_jobs = scan_all(portals_path="portals.yml", conn=conn)
    # new_jobs is a list of dicts matching the posts table schema
"""

import re
import logging
from typing import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import yaml

logger = logging.getLogger(__name__)

FETCH_TIMEOUT = 10  # seconds
MAX_WORKERS = 10


# ── API detection ────────────────────────────────────────────────────

def detect_api(company: dict) -> dict | None:
    """Detect ATS API type from company config.

    Returns {"type": str, "url": str} or None if no API detected.
    """
    # Greenhouse: explicit api field
    api_field = company.get("api", "")
    if api_field and "greenhouse" in api_field:
        return {"type": "greenhouse", "url": api_field}

    url = company.get("careers_url", "")

    # Ashby
    m = re.search(r"jobs\.ashbyhq\.com/([^/?#]+)", url)
    if m:
        slug = m.group(1)
        return {
            "type": "ashby",
            "url": f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true",
        }

    # Lever
    m = re.search(r"jobs\.lever\.co/([^/?#]+)", url)
    if m:
        slug = m.group(1)
        return {
            "type": "lever",
            "url": f"https://api.lever.co/v0/postings/{slug}",
        }

    # Greenhouse (from careers URL, including EU boards)
    m = re.search(r"job-boards(?:\.eu)?\.greenhouse\.io/([^/?#]+)", url)
    if m and not api_field:
        slug = m.group(1)
        return {
            "type": "greenhouse",
            "url": f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
        }

    return None


# ── API parsers ──────────────────────────────────────────────────────

def parse_greenhouse(data: dict, company_name: str) -> list[dict]:
    """Parse Greenhouse board API JSON into normalized job dicts."""
    jobs = data.get("jobs", [])
    return [
        {
            "title": j.get("title", ""),
            "url": j.get("absolute_url", ""),
            "company": company_name,
            "location": (j.get("location") or {}).get("name", ""),
        }
        for j in jobs
    ]


def parse_ashby(data: dict, company_name: str) -> list[dict]:
    """Parse Ashby posting API JSON into normalized job dicts."""
    jobs = data.get("jobs", [])
    return [
        {
            "title": j.get("title", ""),
            "url": j.get("jobUrl", ""),
            "company": company_name,
            "location": j.get("location", ""),
        }
        for j in jobs
    ]


def parse_lever(data, company_name: str) -> list[dict]:
    """Parse Lever postings API JSON into normalized job dicts."""
    if not isinstance(data, list):
        return []
    return [
        {
            "title": j.get("text", ""),
            "url": j.get("hostedUrl", ""),
            "company": company_name,
            "location": (j.get("categories") or {}).get("location", ""),
        }
        for j in data
    ]


_PARSERS = {
    "greenhouse": parse_greenhouse,
    "ashby": parse_ashby,
    "lever": parse_lever,
}


# ── Title filter ─────────────────────────────────────────────────────

def build_title_filter(title_filter: dict) -> Callable:
    """Build a filter function from positive/negative keyword lists.

    Args:
        title_filter: dict with optional 'positive' and 'negative' lists.

    Returns:
        A callable that takes a title string and returns True if it passes.
    """
    positive = [k.lower() for k in (title_filter.get("positive") or [])]
    negative = [k.lower() for k in (title_filter.get("negative") or [])]

    def _filter(title: str) -> bool:
        lower = title.lower()
        has_positive = len(positive) == 0 or any(k in lower for k in positive)
        has_negative = any(k in lower for k in negative)
        return has_positive and not has_negative

    return _filter


# ── Fetch helper ─────────────────────────────────────────────────────

def _fetch_json(url: str) -> dict | list:
    """Fetch JSON from a URL with timeout."""
    resp = requests.get(url, timeout=FETCH_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# ── Normalize to DB schema ───────────────────────────────────────────

def _normalize_job(job: dict) -> dict:
    """Convert a raw parsed job into a dict matching the posts table schema."""
    title = job["title"]
    company_name = job["company"]
    location = job["location"]

    return {
        "author_name": company_name,
        "author_profile": "",
        "author_headline": f"Career page - {company_name}",
        "post_url": job["url"],
        "content": f"[ATS] {title} at {company_name} - {location}",
        "role_hiring_for": title,
        "company": company_name,
        "email": "",
        "location": location,
        "experience": "",
        "domain_relevance": "High",  # all healthcare companies
        "is_hiring": True,
        "keyword_matched": "ats-scan",
        "source": "ats",
    }


# ── Single company scan ─────────────────────────────────────────────

def scan_company(
    company: dict,
    title_filter: Callable,
    seen_urls: set,
    on_event: Callable | None = None,
) -> list[dict]:
    """Scan a single company's ATS API and return new, filtered jobs.

    Args:
        company: Company dict from portals.yml (must have '_api' key).
        title_filter: Callable that returns True if a title passes.
        seen_urls: Set of already-seen job URLs (mutated in place for dedup).
        on_event: Optional callback for progress reporting.

    Returns:
        List of normalized job dicts ready for DB insertion.
    """
    api_info = company.get("_api") or detect_api(company)
    if not api_info:
        return []

    api_type = api_info["type"]
    api_url = api_info["url"]
    company_name = company.get("name", "Unknown")

    if on_event:
        on_event({"type": "scan_start", "company": company_name, "api_type": api_type})

    try:
        data = _fetch_json(api_url)
    except Exception as e:
        logger.warning("Failed to fetch %s (%s): %s", company_name, api_url, e)
        if on_event:
            on_event({"type": "scan_error", "company": company_name, "error": str(e)})
        return []

    parser = _PARSERS.get(api_type)
    if not parser:
        logger.warning("No parser for API type: %s", api_type)
        return []

    raw_jobs = parser(data, company_name)
    results = []

    for job in raw_jobs:
        if not title_filter(job["title"]):
            continue
        if job["url"] in seen_urls:
            continue
        seen_urls.add(job["url"])
        results.append(_normalize_job(job))

    if on_event:
        on_event({
            "type": "scan_done",
            "company": company_name,
            "total": len(raw_jobs),
            "matched": len(results),
        })

    return results


# ── Main scan function ───────────────────────────────────────────────

def scan_all(
    portals_path: str = "config/portals.yml",
    conn=None,
    on_event: Callable | None = None,
) -> list[dict]:
    """Scan all enabled companies from portals.yml.

    Args:
        portals_path: Path to portals.yml config file.
        conn: Optional sqlite3.Connection for dedup against existing posts.
        on_event: Optional callback(dict) for progress reporting.

    Returns:
        List of normalized job dicts matching the posts table schema.
    """
    # 1. Load portals config
    with open(portals_path, "r") as f:
        config = yaml.safe_load(f)

    companies = config.get("tracked_companies", [])
    title_filter_cfg = config.get("title_filter", {})
    title_filter = build_title_filter(title_filter_cfg)

    # 2. Filter to enabled companies with detectable APIs
    targets = []
    for c in companies:
        if c.get("enabled") is False:
            continue
        api_info = detect_api(c)
        if api_info:
            c["_api"] = api_info
            targets.append(c)

    skipped = sum(1 for c in companies if c.get("enabled") is not False) - len(targets)

    if on_event:
        on_event({
            "type": "scan_begin",
            "total_companies": len(targets),
            "skipped": skipped,
        })

    logger.info(
        "Scanning %d companies via API (%d skipped - no API detected)",
        len(targets),
        skipped,
    )

    # 3. Build dedup set from DB
    seen_urls: set[str] = set()
    if conn:
        rows = conn.execute(
            "SELECT post_url FROM posts WHERE post_url IS NOT NULL AND post_url != ''"
        ).fetchall()
        for row in rows:
            seen_urls.add(row[0] if isinstance(row, tuple) else row["post_url"])

    # 4. Fetch all APIs concurrently
    all_jobs: list[dict] = []

    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(targets) or 1)) as executor:
        future_to_company = {
            executor.submit(
                scan_company, company, title_filter, seen_urls, on_event
            ): company
            for company in targets
        }

        for future in as_completed(future_to_company):
            company = future_to_company[future]
            try:
                jobs = future.result()
                all_jobs.extend(jobs)
            except Exception as e:
                logger.error(
                    "Unexpected error scanning %s: %s",
                    company.get("name", "?"),
                    e,
                )
                if on_event:
                    on_event({
                        "type": "scan_error",
                        "company": company.get("name", "?"),
                        "error": str(e),
                    })

    if on_event:
        on_event({"type": "scan_complete", "new_jobs": len(all_jobs)})

    logger.info("ATS scan complete: %d new jobs found", len(all_jobs))
    return all_jobs
