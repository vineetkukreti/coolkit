#!/usr/bin/env python3
"""Full-scale scrape — all API + HTML sources, higher limits, insert to DB."""

import os, sys, time, json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv()

from db import init_db, insert_posts, get_stats
from scrapers.api_scrapers import (
    scrape_remoteok, scrape_himalayas, scrape_hn_hiring,
    scrape_remotive, scrape_wwr_rss, scrape_workingnomads,
    scrape_greenhouse, scrape_lever, scrape_ashby,
)
from scrapers.generic_scrapers import scrape_generic_html
from config_sources import GENERIC_HTML_SOURCES


def run_scraper(name, fn, conn, max_posts, is_html=False, html_key=None):
    """Run a single scraper and insert results into DB."""
    found = 0
    inserted = 0
    skipped_dup = 0
    errors = []
    start = time.time()

    def on_event(evt):
        nonlocal found
        if evt.get("type") == "found":
            found += 1

    try:
        if is_html:
            posts = scrape_generic_html(html_key, None, conn, max_posts=max_posts, on_event=on_event)
        else:
            posts = fn(None, conn, max_posts=max_posts, on_event=on_event)

        if posts:
            ins, skip = insert_posts(conn, posts)
            inserted = ins
            skipped_dup = skip
    except Exception as e:
        errors.append(str(e)[:100])

    elapsed = time.time() - start
    return {
        "name": name,
        "found": found,
        "inserted": inserted,
        "duplicates": skipped_dup,
        "time": round(elapsed, 1),
        "errors": errors,
    }


def main():
    conn = init_db()
    before = get_stats(conn)

    print(f"\n{'='*70}")
    print(f"  FULL-SCALE SCRAPE — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  DB before: {before['total_posts']} posts, {before['hiring']} hiring")
    print(f"{'='*70}\n")

    all_results = []
    total_inserted = 0
    total_found = 0

    # ── Phase 1: API scrapers (max 50 each) ──
    api_scrapers = [
        ("RemoteOK", scrape_remoteok, 50),
        ("Himalayas", scrape_himalayas, 50),
        ("HN Hiring", scrape_hn_hiring, 50),
        ("Remotive", scrape_remotive, 50),
        ("WWR RSS", scrape_wwr_rss, 30),
        ("Working Nomads", scrape_workingnomads, 30),
        ("Greenhouse (33 cos)", scrape_greenhouse, 100),
        ("Lever (3 cos)", scrape_lever, 50),
        ("Ashby (3 cos)", scrape_ashby, 50),
    ]

    print("  Phase 1: API Scrapers\n")
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(run_scraper, name, fn, conn, mp): name
            for name, fn, mp in api_scrapers
        }
        for future in as_completed(futures):
            r = future.result()
            all_results.append(r)
            total_inserted += r["inserted"]
            total_found += r["found"]
            icon = "✅" if r["inserted"] > 0 else ("⚠️" if r["found"] > 0 else "❌")
            err = f" ERR: {r['errors'][0][:40]}" if r["errors"] else ""
            print(f"    {icon} {r['name']:25s} found={r['found']:3d}  new={r['inserted']:3d}  dup={r['duplicates']:3d}  ({r['time']:.0f}s){err}")

    print(f"\n    API subtotal: {total_found} found, {total_inserted} new\n")

    # ── Phase 2: HTML scrapers — test all that passed connectivity ──
    try:
        with open("data/source_test_results.json") as f:
            test_data = json.load(f)
        passing_keys = [k for k, v in test_data.get("details", {}).items()
                        if v.get("status") == "pass" and k in GENERIC_HTML_SOURCES]
    except:
        passing_keys = list(GENERIC_HTML_SOURCES.keys())

    print(f"  Phase 2: HTML Scrapers ({len(passing_keys)} sources)\n")
    html_inserted = 0
    html_found = 0

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(run_scraper, GENERIC_HTML_SOURCES[k]["label"], None, conn, 20, True, k): k
            for k in passing_keys
        }
        for future in as_completed(futures):
            r = future.result()
            all_results.append(r)
            html_inserted += r["inserted"]
            html_found += r["found"]
            total_inserted += r["inserted"]
            total_found += r["found"]
            if r["inserted"] > 0:
                print(f"    ✅ {r['name']:25s} found={r['found']:3d}  new={r['inserted']:3d}  dup={r['duplicates']:3d}  ({r['time']:.0f}s)")
            elif r["found"] > 0:
                print(f"    ⚠️ {r['name']:25s} found={r['found']:3d}  new=  0  dup={r['duplicates']:3d}  ({r['time']:.0f}s)")

    print(f"\n    HTML subtotal: {html_found} found, {html_inserted} new\n")

    # ── Final report ──
    after = get_stats(conn)

    print(f"{'='*70}")
    print(f"  SCRAPE COMPLETE")
    print(f"{'='*70}")
    print(f"  Jobs found:     {total_found}")
    print(f"  New inserted:   {total_inserted}")
    print(f"  Duplicates:     {total_found - total_inserted}")
    print(f"  DB before:      {before['total_posts']} posts")
    print(f"  DB after:       {after['total_posts']} posts (+{after['total_posts'] - before['total_posts']})")
    print(f"  Hiring posts:   {after['hiring']}")
    print(f"{'='*70}")

    # Top producers
    all_results.sort(key=lambda r: -r["inserted"])
    print(f"\n  TOP PRODUCERS (by new jobs):")
    for r in all_results[:20]:
        if r["inserted"] > 0:
            print(f"    {r['inserted']:4d} new — {r['name']}")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_found": total_found,
        "total_inserted": total_inserted,
        "db_before": before["total_posts"],
        "db_after": after["total_posts"],
        "results": all_results,
    }
    with open("data/full_scrape_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report saved: data/full_scrape_report.json")


if __name__ == "__main__":
    main()
