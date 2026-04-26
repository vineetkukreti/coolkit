#!/usr/bin/env python3
"""
Live scrape test — run all working API + HTML scrapers and count actual jobs extracted.
Tests the FULL pipeline: fetch → parse → dedup → fitness check → count.
"""

import os, sys, time, json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv()

from db import init_db
from scrapers.api_scrapers import (
    scrape_remoteok, scrape_himalayas, scrape_hn_hiring,
    scrape_remotive, scrape_wwr_rss, scrape_workingnomads,
    scrape_greenhouse, scrape_lever, scrape_ashby,
)
from scrapers.generic_scrapers import scrape_generic_html
from config_sources import GENERIC_HTML_SOURCES


def make_counter():
    """Create an event counter callback."""
    stats = {"found": 0, "skip": 0, "extract": 0, "error": 0}
    def on_event(evt):
        t = evt.get("type", "")
        if t == "found":
            stats["found"] += 1
        elif t == "skip":
            stats["skip"] += 1
        elif t == "extract":
            stats["extract"] += evt.get("count", 0)
        elif t == "error":
            stats["error"] += 1
    return stats, on_event


def test_api_scraper(name, fn, conn, max_posts=15):
    """Test a custom API scraper."""
    stats, cb = make_counter()
    start = time.time()
    try:
        posts = fn(None, conn, max_posts=max_posts, on_event=cb)
        elapsed = time.time() - start
        return name, len(posts), stats, elapsed, None
    except Exception as e:
        elapsed = time.time() - start
        return name, 0, stats, elapsed, str(e)[:100]


def test_html_scraper(key, conn, max_posts=10):
    """Test a generic HTML scraper."""
    stats, cb = make_counter()
    start = time.time()
    try:
        posts = scrape_generic_html(key, None, conn, max_posts=max_posts, on_event=cb)
        elapsed = time.time() - start
        return key, len(posts), stats, elapsed, None
    except Exception as e:
        elapsed = time.time() - start
        return key, 0, stats, elapsed, str(e)[:100]


def main():
    conn = init_db()
    print(f"\n{'='*70}")
    print(f"  LIVE SCRAPE TEST — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    # ── Phase 1: Test custom API scrapers ──
    api_scrapers = [
        ("RemoteOK", scrape_remoteok),
        ("Himalayas", scrape_himalayas),
        ("HN Hiring", scrape_hn_hiring),
        ("Remotive", scrape_remotive),
        ("WWR RSS", scrape_wwr_rss),
        ("Working Nomads", scrape_workingnomads),
        ("Greenhouse", scrape_greenhouse),
        ("Lever", scrape_lever),
        ("Ashby", scrape_ashby),
    ]

    print("  ── PHASE 1: Custom API Scrapers ──\n")
    api_total = 0
    api_results = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(test_api_scraper, name, fn, conn, 15): name for name, fn in api_scrapers}
        for future in as_completed(futures):
            name, count, stats, elapsed, error = future.result()
            api_total += count
            icon = "✅" if count > 0 else ("❌" if error else "⚠️")
            err_msg = f" ERR: {error}" if error else ""
            print(f"    {icon} {name:20s} {count:3d} jobs  (extracted={stats['extract']}, skipped={stats['skip']}, {elapsed:.1f}s){err_msg}")
            api_results.append({"name": name, "jobs": count, "time": round(elapsed, 1), "error": error})

    print(f"\n    API Total: {api_total} jobs from {len(api_scrapers)} scrapers\n")

    # ── Phase 2: Test generic HTML scrapers (top 30 most likely to work) ──
    # Pick sources that passed the connectivity test
    test_keys = []
    try:
        with open("data/source_test_results.json") as f:
            test_data = json.load(f)
        details = test_data.get("details", {})
        for key in GENERIC_HTML_SOURCES:
            if key in details and details[key].get("status") == "pass":
                test_keys.append(key)
    except:
        test_keys = list(GENERIC_HTML_SOURCES.keys())[:30]

    # Limit to 30 to avoid taking forever
    test_keys = test_keys[:30]

    print(f"  ── PHASE 2: Generic HTML Scrapers ({len(test_keys)} sources) ──\n")
    html_total = 0
    html_results = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(test_html_scraper, key, conn, 10): key for key in test_keys}
        for future in as_completed(futures):
            key, count, stats, elapsed, error = future.result()
            html_total += count
            label = GENERIC_HTML_SOURCES.get(key, {}).get("label", key)
            icon = "✅" if count > 0 else ("❌" if error else "⚠️")
            err_msg = f" ERR: {error[:50]}" if error else ""
            print(f"    {icon} {label:25s} {count:3d} jobs  (extracted={stats['extract']}, skip={stats['skip']}, {elapsed:.1f}s){err_msg}")
            html_results.append({"name": label, "key": key, "jobs": count, "time": round(elapsed, 1), "error": error})

    print(f"\n    HTML Total: {html_total} jobs from {len(test_keys)} scrapers\n")

    # ── Summary ──
    grand_total = api_total + html_total
    working_api = sum(1 for r in api_results if r["jobs"] > 0)
    working_html = sum(1 for r in html_results if r["jobs"] > 0)

    print(f"{'='*70}")
    print(f"  GRAND TOTAL: {grand_total} jobs extracted")
    print(f"  Working scrapers: {working_api + working_html} / {len(api_scrapers) + len(test_keys)}")
    print(f"    API:  {working_api}/{len(api_scrapers)} scrapers → {api_total} jobs")
    print(f"    HTML: {working_html}/{len(test_keys)} scrapers → {html_total} jobs")
    print(f"  + 18 custom browser scrapers (LinkedIn, Naukri, Indeed, etc.) not tested here")
    print(f"{'='*70}")

    # Top producers
    all_results = api_results + html_results
    all_results.sort(key=lambda r: -r["jobs"])
    print(f"\n  TOP 15 PRODUCERS:")
    for r in all_results[:15]:
        if r["jobs"] > 0:
            print(f"    {r['jobs']:4d} jobs — {r['name']}")

    # Save
    report = {
        "timestamp": datetime.now().isoformat(),
        "grand_total": grand_total,
        "api_total": api_total,
        "html_total": html_total,
        "working_api": working_api,
        "working_html": working_html,
        "api_results": api_results,
        "html_results": html_results,
    }
    with open("data/live_scrape_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Full results saved: data/live_scrape_results.json")


if __name__ == "__main__":
    main()
