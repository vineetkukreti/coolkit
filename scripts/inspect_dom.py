#!/usr/bin/env python3
"""
DOM Inspector — visit all failing/empty sites and capture actual structure.
Outputs a JSON with correct selectors for each site.
"""

import os, sys, json, time, re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def inspect_site(key, url, base_url=""):
    """Visit a site and auto-detect job listing selectors."""
    result = {"key": key, "url": url, "status": "unknown", "selectors": None}

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        result["http_status"] = resp.status_code
        result["final_url"] = resp.url

        if resp.status_code == 403:
            result["status"] = "blocked"
            return result
        if resp.status_code == 404:
            result["status"] = "not_found"
            return result
        if resp.status_code not in (200, 202):
            result["status"] = f"http_{resp.status_code}"
            return result

        text = resp.text
        if len(text) < 500:
            result["status"] = "too_short"
            return result
        if "Just a moment" in text[:1000] or "Verification Required" in text[:1000]:
            result["status"] = "cloudflare"
            return result
        if "challenge" in text[:2000].lower() and "captcha" in text[:5000].lower():
            result["status"] = "captcha"
            return result

        soup = BeautifulSoup(text, "html.parser")
        body_text = soup.get_text(strip=True)

        if len(body_text) < 50:
            result["status"] = "empty_body"
            return result

        # ─── Auto-detect job cards ───
        # Strategy 1: Find all links that look like job URLs
        job_link_patterns = [
            r'/jobs?/', r'/job/', r'/position', r'/vacancy', r'/career',
            r'/opening', r'/posting', r'/listing', r'/role/',
        ]
        job_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if any(re.search(p, href) for p in job_link_patterns):
                job_links.append(a)

        # Strategy 2: Find repeated structural elements (cards)
        # Look for the most common parent containers of job links
        card_candidates = {}
        for a in job_links[:30]:
            # Walk up 1-5 levels to find card container
            for depth in range(1, 6):
                parent = a
                for _ in range(depth):
                    parent = parent.parent
                    if parent is None or parent.name in ("body", "html", "main", "section", "div"):
                        if parent and parent.name == "div" and parent.get("class"):
                            break
                        continue
                if parent and parent.name:
                    # Build selector from tag + class
                    tag = parent.name
                    classes = parent.get("class", [])
                    if classes:
                        sel = f"{tag}.{classes[0]}"
                    else:
                        sel = tag
                    # Count how many siblings match
                    if sel not in card_candidates:
                        count = len(soup.select(sel))
                        if count >= 2:
                            card_candidates[sel] = count

        # Strategy 3: Common patterns
        common_card_sels = [
            "article", "li.job", "div.job-card", "div.job-listing",
            "tr", "div.result", "div.card", "a.job",
            "[class*='job']", "[class*='listing']", "[class*='card']",
            "[class*='result']", "[class*='posting']",
        ]
        for sel in common_card_sels:
            try:
                matches = soup.select(sel)
                if 2 <= len(matches) <= 200:
                    card_candidates[sel] = len(matches)
            except Exception:
                pass

        if not card_candidates and not job_links:
            # Check if it's an SPA
            scripts = soup.find_all("script")
            is_spa = any("react" in str(s).lower() or "__next" in str(s) or "vue" in str(s).lower() for s in scripts)
            result["status"] = "spa_needs_browser" if is_spa else "no_jobs_found"
            result["body_len"] = len(body_text)
            result["job_links"] = len(job_links)
            return result

        # Pick the best card selector (most matches in a reasonable range)
        best_card = None
        best_count = 0
        for sel, count in sorted(card_candidates.items(), key=lambda x: -x[1]):
            if 2 <= count <= 100:
                best_card = sel
                best_count = count
                break
        if not best_card and card_candidates:
            best_card = max(card_candidates, key=card_candidates.get)
            best_count = card_candidates[best_card]

        # Now find title/company/location selectors within the card
        title_sel = None
        company_sel = None
        location_sel = None
        link_sel = None
        sample_title = ""

        if best_card:
            cards = soup.select(best_card)[:5]
            for card in cards:
                # Title: look for h2, h3, h4 with links, or prominent link
                for ts in ["h2 a", "h3 a", "h4 a", "h2", "h3", "a[class*='title']",
                           "a[class*='name']", "span[class*='title']", "div[class*='title']"]:
                    el = card.select_one(ts)
                    if el and el.get_text(strip=True):
                        title_sel = ts
                        sample_title = el.get_text(strip=True)[:60]
                        break

                # Link: the title link or first job-like link
                if not link_sel:
                    for ls in ["h2 a", "h3 a", "h4 a", "a[class*='title']", "a[href*='job']",
                               "a[href*='position']", "a[href*='career']", "a[href]"]:
                        el = card.select_one(ls)
                        if el and el.get("href"):
                            link_sel = ls
                            break

                # Company
                if not company_sel:
                    for cs in ["[class*='company']", "[class*='employer']", "[class*='org']",
                               "[class*='comp']", "span.company", "div.company"]:
                        el = card.select_one(cs)
                        if el and el.get_text(strip=True):
                            company_sel = cs
                            break

                # Location
                if not location_sel:
                    for locs in ["[class*='location']", "[class*='loc']", "[class*='region']",
                                 "[class*='place']", "span.location", "div.location"]:
                        el = card.select_one(locs)
                        if el and el.get_text(strip=True):
                            location_sel = locs
                            break

                if title_sel:
                    break

        result["status"] = "detected"
        result["selectors"] = {
            "card": best_card or "article",
            "title": title_sel or "h2 a, h3 a",
            "company": company_sel or "[class*='company']",
            "location": location_sel or "[class*='location']",
            "link": link_sel or "a[href]",
        }
        result["card_count"] = best_count
        result["job_links_count"] = len(job_links)
        result["sample_title"] = sample_title
        result["body_len"] = len(body_text)

    except requests.Timeout:
        result["status"] = "timeout"
    except requests.ConnectionError:
        result["status"] = "connection_error"
    except Exception as e:
        result["status"] = f"error: {str(e)[:100]}"

    return result


def main():
    from config_sources import GENERIC_HTML_SOURCES

    # Build list of sites to inspect
    sites = []
    for key, config in GENERIC_HTML_SOURCES.items():
        urls = config.get("urls", [])
        if urls:
            sites.append((key, urls[0], config.get("base_url", "")))

    print(f"Inspecting {len(sites)} HTML sources...\n")

    all_results = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(inspect_site, key, url, base): key for key, url, base in sites}
        done = 0
        for future in as_completed(futures):
            done += 1
            result = future.result()
            key = result["key"]
            status = result["status"]
            all_results[key] = result

            icon = {"detected": "✅", "blocked": "🚫", "cloudflare": "🚫", "captcha": "🚫",
                    "not_found": "❌", "timeout": "⏳", "connection_error": "❌",
                    "spa_needs_browser": "🌐", "empty_body": "⚠️", "too_short": "⚠️",
                    "no_jobs_found": "⚠️"}.get(status, "❓")

            extra = ""
            if status == "detected":
                extra = f"cards={result.get('card_count', 0)} sel={result['selectors']['card'][:30]} title=\"{result.get('sample_title', '')[:30]}\""
            print(f"  [{done:2d}/{len(sites)}] {icon} {key:25s} {status:20s} {extra}")

    # Save results
    with open("data/dom_inspection.json", "w") as f:
        json.dump(all_results, f, indent=2)

    # Summary
    detected = [k for k, r in all_results.items() if r["status"] == "detected"]
    blocked = [k for k, r in all_results.items() if r["status"] in ("blocked", "cloudflare", "captcha")]
    spa = [k for k, r in all_results.items() if r["status"] == "spa_needs_browser"]
    failed = [k for k, r in all_results.items() if r["status"] in ("not_found", "timeout", "connection_error", "too_short", "empty_body")]
    no_jobs = [k for k, r in all_results.items() if r["status"] == "no_jobs_found"]

    print(f"\n{'='*50}")
    print(f"  Detected:         {len(detected)}")
    print(f"  Blocked:          {len(blocked)}")
    print(f"  SPA (browser):    {len(spa)}")
    print(f"  No jobs found:    {len(no_jobs)}")
    print(f"  Failed:           {len(failed)}")

    # Generate updated selectors
    print(f"\n--- SELECTOR UPDATES ---")
    for key in detected:
        r = all_results[key]
        sel = r["selectors"]
        print(f'    "{key}": {{"card": "{sel["card"]}", "title": "{sel["title"]}", "company": "{sel["company"]}", "location": "{sel["location"]}", "link": "{sel["link"]}"}},')

    print(f"\n--- BLOCKED (need browser/proxy/alternatives) ---")
    for key in blocked:
        print(f"    {key}")

    print(f"\n--- SPA (need Playwright browser) ---")
    for key in spa:
        print(f"    {key}")

    print(f"\n--- FAILED (need URL fix or replacement) ---")
    for key in failed:
        r = all_results[key]
        print(f"    {key}: {r['status']} — {r.get('url', '')[:60]}")


if __name__ == "__main__":
    main()
