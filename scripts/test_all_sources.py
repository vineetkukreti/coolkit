#!/usr/bin/env python3
"""
Test all 100 job portal sources — verify connectivity, selectors, and data extraction.

Tests:
  - API scrapers: Hit endpoint, check JSON response, verify job data
  - HTML scrapers: Fetch page, parse with BeautifulSoup, check selectors
  - Reports: PASS / FAIL / BLOCKED / EMPTY for each source
"""

import os, sys, time, json, re
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import requests
from bs4 import BeautifulSoup

from config_sources import (
    CUSTOM_SOURCES, GENERIC_HTML_SOURCES, GENERIC_API_SOURCES,
    SOURCE_GROUPS, get_all_sources, get_source_count,
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ─── Results tracking ────────────────────────────────────────────────────────
results = {
    "pass": [],       # Working — found jobs
    "empty": [],      # Reachable but no jobs found (selectors may need tuning)
    "blocked": [],    # Cloudflare / CAPTCHA / 403
    "fail": [],       # Error / unreachable
    "skip": [],       # Custom scrapers (need browser/special handling)
}


def test_api_endpoint(key, url, jobs_path="", fields=None):
    """Test a JSON API endpoint."""
    try:
        resp = requests.get(url, headers={**HEADERS, "Accept": "application/json"}, timeout=12)
        if resp.status_code == 403:
            return "blocked", f"HTTP 403 (Cloudflare/blocked)"
        if resp.status_code == 404:
            return "fail", f"HTTP 404"
        if resp.status_code != 200:
            return "fail", f"HTTP {resp.status_code}"

        ct = resp.headers.get("content-type", "")
        if "json" not in ct and "javascript" not in ct:
            # Check for Cloudflare challenge page
            if "Just a moment" in resp.text[:500] or "challenge" in resp.text[:500].lower():
                return "blocked", "Cloudflare challenge page"
            return "fail", f"Not JSON: {ct[:50]}"

        data = resp.json()

        # Navigate to jobs list
        jobs = data
        if jobs_path:
            for part in jobs_path.split("."):
                if isinstance(jobs, dict):
                    jobs = jobs.get(part, [])
                elif isinstance(jobs, list) and part.isdigit():
                    idx = int(part)
                    jobs = jobs[idx] if idx < len(jobs) else []

        if isinstance(jobs, list):
            count = len(jobs)
            if count > 0:
                sample = jobs[0] if isinstance(jobs[0], dict) else {}
                sample_keys = list(sample.keys())[:5]
                return "pass", f"{count} jobs found. Sample keys: {sample_keys}"
            return "empty", "0 jobs in response"
        elif isinstance(jobs, dict):
            return "pass", f"Got dict response with keys: {list(jobs.keys())[:5]}"
        return "empty", "Unexpected response format"

    except requests.Timeout:
        return "fail", "Timeout (12s)"
    except requests.ConnectionError as e:
        return "fail", f"Connection error: {str(e)[:80]}"
    except Exception as e:
        return "fail", f"Error: {str(e)[:100]}"


def test_html_page(key, config):
    """Test an HTML scraper by fetching the page and checking selectors."""
    urls = config.get("urls", [])
    if not urls:
        return "fail", "No URLs configured"

    url = urls[0]
    sel = config.get("selectors", {})
    base_url = config.get("base_url", "")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        if resp.status_code == 403:
            return "blocked", "HTTP 403"
        if resp.status_code == 404:
            return "fail", "HTTP 404"
        if resp.status_code != 200:
            return "fail", f"HTTP {resp.status_code}"

        # Check for Cloudflare / CAPTCHA
        text = resp.text[:2000]
        if "Just a moment" in text or "Verification Required" in text:
            return "blocked", "Cloudflare/CAPTCHA challenge"
        if "challenge-platform" in text or "cf-browser-verification" in text:
            return "blocked", "Cloudflare challenge"
        if "Please enable JS" in text and len(resp.text) < 3000:
            return "blocked", "JS challenge (anti-bot)"

        soup = BeautifulSoup(resp.text, "html.parser")

        # Check body has content
        body_text = soup.get_text(strip=True)
        if len(body_text) < 100:
            return "blocked", f"Nearly empty page ({len(body_text)} chars)"

        # Test card selector
        card_sel = sel.get("card", "article")
        cards = soup.select(card_sel)

        if cards:
            # Test title selector on first card
            title_sel = sel.get("title", "h2 a")
            titles_found = 0
            links_found = 0
            sample_title = ""

            for card in cards[:5]:
                title_el = card.select_one(title_sel)
                if title_el:
                    titles_found += 1
                    if not sample_title:
                        sample_title = title_el.get_text(strip=True)[:60]

                link_sel = sel.get("link", "a[href]")
                link_el = card.select_one(link_sel)
                if link_el and link_el.get("href"):
                    links_found += 1

            if titles_found > 0:
                return "pass", f"{len(cards)} cards, {titles_found}/5 titles, {links_found}/5 links. Sample: \"{sample_title}\""
            else:
                return "empty", f"{len(cards)} cards found but title selector '{title_sel}' matched 0. Page has content — selectors need tuning."
        else:
            # Cards not found — try to detect if page is SPA
            scripts = soup.find_all("script")
            has_react = any("react" in str(s).lower() or "__next" in str(s) for s in scripts)
            has_vue = any("vue" in str(s).lower() for s in scripts)

            if has_react or has_vue:
                return "empty", f"SPA detected (React/Vue) — needs browser rendering. Card selector '{card_sel}' matched 0."
            else:
                # Try generic fallback selectors
                fallback = soup.select("a[href*='job'], a[href*='career'], a[href*='position']")
                if fallback:
                    return "empty", f"Card selector '{card_sel}' matched 0, but found {len(fallback)} job-like links. Selectors need tuning."
                return "empty", f"Card selector '{card_sel}' matched 0. Body text: {len(body_text)} chars."

    except requests.Timeout:
        return "fail", "Timeout (12s)"
    except requests.ConnectionError as e:
        return "fail", f"Connection error: {str(e)[:80]}"
    except Exception as e:
        return "fail", f"Error: {str(e)[:100]}"


def test_custom_api_source(key):
    """Test known custom API scrapers by hitting their endpoints."""
    endpoints = {
        "remoteok": ("https://remoteok.com/api", ""),
        "himalayas": ("https://himalayas.app/jobs/api?limit=5&query=AI", "jobs"),
        "remotive": ("https://remotive.com/api/remote-jobs?category=software-dev&limit=5", "jobs"),
        "workingnomads": ("https://www.workingnomads.com/api/exposed_jobs/", ""),
        "greenhouse": ("https://boards-api.greenhouse.io/v1/boards/anthropic/jobs", "jobs"),
        "lever": ("https://api.lever.co/v0/postings/Netflix?mode=json", ""),
        "ashby": ("https://api.ashbyhq.com/posting-api/job-board/anthropic", "jobs"),
    }
    if key in endpoints:
        url, path = endpoints[key]
        return test_api_endpoint(key, url, path)
    return "skip", "Custom scraper — needs browser or special handling"


def run_test(key, source_info):
    """Run test for a single source. Returns (key, status, message)."""
    engine = source_info.get("engine", "custom")

    if engine == "generic_html":
        config = GENERIC_HTML_SOURCES.get(key, {})
        status, msg = test_html_page(key, config)
    elif engine == "generic_api":
        config = GENERIC_API_SOURCES.get(key, {})
        # Build test URL
        url = config.get("url", "").format(query="AI+Engineer")
        status, msg = test_api_endpoint(key, url, config.get("jobs_path", ""))
    elif engine == "custom":
        status, msg = test_custom_api_source(key)
    else:
        status, msg = "skip", f"Unknown engine: {engine}"

    return key, status, msg


def main():
    all_sources = get_all_sources()
    total = get_source_count()

    print(f"\n{'='*70}")
    print(f"  TESTING ALL {total} JOB PORTAL SOURCES")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    # Run tests in parallel (max 10 threads to avoid IP issues)
    test_results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        for key, info in all_sources.items():
            future = executor.submit(run_test, key, info)
            futures[future] = key

        done_count = 0
        for future in as_completed(futures):
            done_count += 1
            key = futures[future]
            try:
                key, status, msg = future.result()
            except Exception as e:
                key, status, msg = key, "fail", f"Test crashed: {str(e)[:100]}"

            test_results.append((key, status, msg))
            label = all_sources[key]["label"]

            icon = {"pass": "✅", "empty": "⚠️", "blocked": "🚫", "fail": "❌", "skip": "⏭️"}.get(status, "?")
            print(f"  [{done_count:3d}/{total}] {icon} {label:30s} {status:8s} {msg[:70]}")

            results[status].append((key, label, msg))

    # ─── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"  ✅ PASS:    {len(results['pass']):3d}  (working, found jobs)")
    print(f"  ⚠️  EMPTY:   {len(results['empty']):3d}  (reachable, selectors need tuning)")
    print(f"  🚫 BLOCKED: {len(results['blocked']):3d}  (Cloudflare/CAPTCHA)")
    print(f"  ❌ FAIL:    {len(results['fail']):3d}  (error/unreachable)")
    print(f"  ⏭️  SKIP:    {len(results['skip']):3d}  (needs browser)")
    print(f"  {'─'*40}")
    print(f"  TOTAL:     {total:3d}")

    # Details for each category
    if results["pass"]:
        print(f"\n  ✅ WORKING ({len(results['pass'])}):")
        for key, label, msg in sorted(results["pass"], key=lambda x: x[1]):
            print(f"     {label:30s} {msg[:60]}")

    if results["blocked"]:
        print(f"\n  🚫 BLOCKED ({len(results['blocked'])}):")
        for key, label, msg in sorted(results["blocked"], key=lambda x: x[1]):
            print(f"     {label:30s} {msg[:60]}")

    if results["fail"]:
        print(f"\n  ❌ FAILED ({len(results['fail'])}):")
        for key, label, msg in sorted(results["fail"], key=lambda x: x[1]):
            print(f"     {label:30s} {msg[:60]}")

    if results["empty"]:
        print(f"\n  ⚠️  EMPTY/NEEDS TUNING ({len(results['empty'])}):")
        for key, label, msg in sorted(results["empty"], key=lambda x: x[1]):
            print(f"     {label:30s} {msg[:60]}")

    if results["skip"]:
        print(f"\n  ⏭️  SKIPPED ({len(results['skip'])}):")
        for key, label, msg in sorted(results["skip"], key=lambda x: x[1]):
            print(f"     {label:30s} {msg[:60]}")

    # Save results
    report = {
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "pass": len(results["pass"]),
        "empty": len(results["empty"]),
        "blocked": len(results["blocked"]),
        "fail": len(results["fail"]),
        "skip": len(results["skip"]),
        "details": {k: {"status": s, "message": m} for k, s, m in test_results},
    }
    with open("data/source_test_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Full results saved: data/source_test_results.json")
    print()


if __name__ == "__main__":
    main()
