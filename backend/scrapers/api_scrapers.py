"""
API-Based Job Scrapers
-----------------------
Scrapers that use REST APIs instead of browser automation.
No Playwright needed — faster, cheaper, no rate-limit risk.

All scrapers follow the same interface:
    scrape_<platform>(page, conn, max_posts, on_event) -> list[dict]
    (page is unused — kept for interface compatibility)
"""

import re
import time
import random
import requests
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus
from rich.console import Console

from db import content_hash, DedupCache
from post_parser import (
    llm_extract, extract_roles, extract_location,
    extract_emails, score_domain_relevance,
    is_good_fit,
)

console = Console()

# ─── Freshness filter — skip jobs older than this ────────────────────────────
MAX_JOB_AGE_DAYS = 14

def _is_fresh(date_str: str) -> bool:
    """Check if a job date string is within MAX_JOB_AGE_DAYS. Returns True if fresh or unparseable."""
    if not date_str:
        return True  # No date = assume fresh
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_JOB_AGE_DAYS)
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%b %d, %Y", "%d %b %Y",
        "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT",
    ):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt >= cutoff
        except ValueError:
            continue
    # Try Unix timestamp
    try:
        ts = int(date_str)
        if ts > 1_000_000_000:
            return datetime.fromtimestamp(ts, tz=timezone.utc) >= cutoff
    except (ValueError, TypeError):
        pass
    return True  # Can't parse = assume fresh

_API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def _make_emit(on_event):
    def emit(evt):
        if on_event:
            try:
                on_event(evt)
            except Exception:
                pass
    return emit


def _process_api_job(
    job_url: str, title: str, company: str, location: str,
    desc: str, source: str, term: str,
    dedup, all_posts: list, emit,
) -> bool:
    """Shared processing for API-sourced jobs. Returns True if added."""
    content = f"{title} at {company}. {desc}. Location: {location}".strip()
    if len(content) < 20:
        return False

    c_hash = content_hash(content)
    if dedup.exists(job_url, c_hash, content):
        return False

    domain = score_domain_relevance(content)

    # LLM extraction for richer data — only for relevant jobs
    llm = {}
    if len(content) > 50 and domain in ("High", "Medium"):
        llm = llm_extract(content)

    roles = llm.get("role") or extract_roles(content)
    if roles == "Not specified":
        roles = title
    loc = llm.get("location") or extract_location(content) or location
    comp = llm.get("company") or company
    exp = llm.get("experience", "")
    emails = extract_emails(content)

    fit, reason = is_good_fit(roles, exp)
    if not fit:
        emit({"type": "skip", "author": (comp or title)[:20], "reason": reason})
        return False

    data = {
        "sno": len(all_posts) + 1,
        "author_name": comp or "Unknown",
        "author_profile": job_url,
        "author_headline": f"Found via {source}",
        "post_url": job_url,
        "content": content,
        "role_hiring_for": roles,
        "company": comp,
        "email": emails or "",
        "location": loc,
        "experience": exp,
        "domain_relevance": domain,
        "post_date": "",
        "keyword_matched": term,
        "is_hiring": True,
        "source": source.lower(),
    }

    all_posts.append(data)
    dedup.add(job_url, c_hash, content)

    emit({
        "type": "found",
        "sno": data["sno"],
        "author": (comp or title)[:25],
        "role": roles[:25],
        "company": comp[:20],
        "email": (emails or "")[:25],
        "domain": domain,
        "source": source,
    })
    return True


# ─── RemoteOK Scraper ────────────────────────────────────────────────────────

def scrape_remoteok(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape RemoteOK via their free JSON API. No auth required."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = _make_emit(on_event)

    emit({"type": "info", "message": "Fetching RemoteOK API..."})

    search_tags = [
        "ai", "machine-learning", "python", "data-science",
        "nlp", "deep-learning", "engineer",
    ]

    for si, tag in enumerate(search_tags):
        if len(all_posts) >= max_posts:
            break

        emit({"type": "search", "query": f"RemoteOK tag={tag}", "index": si + 1, "total": len(search_tags)})

        try:
            url = f"https://remoteok.com/api?tag={tag}"
            resp = requests.get(url, headers=_API_HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            emit({"type": "error", "message": f"RemoteOK API error: {str(e)[:200]}"})
            continue

        # First element is metadata/legal notice
        jobs = data[1:] if len(data) > 1 else []
        emit({"type": "extract", "count": len(jobs)})

        for job in jobs:
            if len(all_posts) >= max_posts:
                break

            job_url = job.get("url", "")
            if not job_url and job.get("id"):
                job_url = f"https://remoteok.com/remote-jobs/{job['id']}"

            # Freshness check — skip old jobs
            job_date = job.get("date", "") or str(job.get("epoch", ""))
            if not _is_fresh(job_date):
                continue

            title = job.get("position", "")
            company = job.get("company", "")
            location = job.get("location", "Remote")
            desc = job.get("description", "")
            # Strip HTML tags from description
            desc = re.sub(r'<[^>]+>', ' ', desc)[:500]
            tags = ", ".join(job.get("tags", []))
            if tags:
                desc += f"\nSkills: {tags}"

            _process_api_job(
                job_url, title, company, location, desc,
                "RemoteOK", tag, dedup, all_posts, emit,
            )

        time.sleep(random.uniform(1, 2))

    emit({"type": "done", "total": len(all_posts), "queries_searched": len(search_tags),
          "message": f"RemoteOK complete: {len(all_posts)} posts collected"})
    return all_posts


# ─── Himalayas Scraper ────────────────────────────────────────────────────────

def scrape_himalayas(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape Himalayas via their free JSON API. No auth required."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = _make_emit(on_event)

    emit({"type": "info", "message": "Fetching Himalayas API..."})

    search_terms = [
        "AI Engineer", "Machine Learning", "Data Scientist",
        "NLP Engineer", "Deep Learning", "Python Engineer",
        "GenAI", "LLM",
    ]

    for si, term in enumerate(search_terms):
        if len(all_posts) >= max_posts:
            break

        emit({"type": "search", "query": f"Himalayas: {term}", "index": si + 1, "total": len(search_terms)})

        offset = 0
        page_size = 50

        while len(all_posts) < max_posts:
            try:
                url = f"https://himalayas.app/jobs/api?limit={page_size}&offset={offset}&query={quote_plus(term)}"
                resp = requests.get(url, headers=_API_HEADERS, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                emit({"type": "error", "message": f"Himalayas API error: {str(e)[:200]}"})
                break

            jobs = data.get("jobs", [])
            if not jobs:
                break

            emit({"type": "extract", "count": len(jobs)})

            for job in jobs:
                if len(all_posts) >= max_posts:
                    break

                title = job.get("title", "")
                company = job.get("companyName", "") or job.get("company_name", "")
                location = job.get("locationRestrictions", "") or "Remote"
                if isinstance(location, list):
                    location = ", ".join(location) if location else "Remote"
                desc = job.get("excerpt", "") or job.get("description", "")[:500]
                job_url = job.get("applicationLink", "") or f"https://himalayas.app/jobs/{job.get('id', '')}"

                _process_api_job(
                    job_url, title, company, location, desc,
                    "Himalayas", term, dedup, all_posts, emit,
                )

            offset += page_size
            if len(jobs) < page_size:
                break
            time.sleep(random.uniform(0.5, 1.5))

        time.sleep(random.uniform(1, 2))

    emit({"type": "done", "total": len(all_posts), "queries_searched": len(search_terms),
          "message": f"Himalayas complete: {len(all_posts)} posts collected"})
    return all_posts


# ─── HN Who is Hiring Scraper ────────────────────────────────────────────────

def scrape_hn_hiring(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape Hacker News 'Who is Hiring' threads via Algolia API."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = _make_emit(on_event)

    emit({"type": "info", "message": "Finding latest HN 'Who is Hiring' thread..."})

    # Step 1: Find the latest "Ask HN: Who is hiring?" post
    try:
        search_url = (
            "https://hn.algolia.com/api/v1/search?"
            "query=%22Ask%20HN%3A%20Who%20is%20hiring%22"
            "&tags=ask_hn"
            "&numericFilters=created_at_i>0"
            "&hitsPerPage=5"
        )
        resp = requests.get(search_url, headers=_API_HEADERS, timeout=15)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
    except Exception as e:
        emit({"type": "error", "message": f"HN search error: {str(e)[:200]}"})
        return all_posts

    if not hits:
        emit({"type": "error", "message": "No 'Who is Hiring' threads found"})
        return all_posts

    # Use the most recent thread
    thread = hits[0]
    thread_id = thread.get("objectID", "")
    thread_title = thread.get("title", "Who is Hiring")
    emit({"type": "info", "message": f"Found: {thread_title} (ID: {thread_id})"})

    # Step 2: Fetch all comments (each comment = one job posting)
    comment_page = 0
    total_fetched = 0

    while len(all_posts) < max_posts:
        try:
            comments_url = (
                f"https://hn.algolia.com/api/v1/search?"
                f"tags=comment,story_{thread_id}"
                f"&hitsPerPage=100&page={comment_page}"
            )
            resp = requests.get(comments_url, headers=_API_HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            emit({"type": "error", "message": f"HN comments error: {str(e)[:200]}"})
            break

        comments = data.get("hits", [])
        if not comments:
            break

        total_fetched += len(comments)
        emit({"type": "search", "query": f"HN comments page {comment_page + 1}", "index": comment_page + 1, "total": data.get("nbPages", 1)})
        emit({"type": "extract", "count": len(comments)})

        for comment in comments:
            if len(all_posts) >= max_posts:
                break

            text = comment.get("comment_text", "")
            if not text or len(text) < 50:
                continue

            # Strip HTML
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()

            # HN hiring posts typically start with "Company | Role | Location"
            job_url = f"https://news.ycombinator.com/item?id={comment.get('objectID', '')}"

            # Try to parse the "Company | Role | Location" format
            first_line = text.split('.')[0] if '.' in text else text[:100]
            parts = [p.strip() for p in first_line.split('|')]

            company = parts[0][:50] if len(parts) >= 1 else ""
            title = parts[1][:50] if len(parts) >= 2 else "Software Engineer"
            location = parts[2][:50] if len(parts) >= 3 else "Remote"

            _process_api_job(
                job_url, title, company, location, text[:500],
                "HN", thread_title[:30], dedup, all_posts, emit,
            )

        comment_page += 1
        if comment_page >= data.get("nbPages", 1):
            break
        time.sleep(random.uniform(0.5, 1))

    emit({"type": "done", "total": len(all_posts), "queries_searched": total_fetched,
          "message": f"HN Who is Hiring complete: {len(all_posts)} posts from {total_fetched} comments"})
    return all_posts


# ─── Remotive Scraper ─────────────────────────────────────────────────────────

def scrape_remotive(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape Remotive via their free JSON API. No auth needed."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = _make_emit(on_event)

    categories = ["software-dev", "data", "devops", "all"]
    emit({"type": "info", "message": "Fetching Remotive API..."})

    for si, cat in enumerate(categories):
        if len(all_posts) >= max_posts:
            break
        emit({"type": "search", "query": f"Remotive: {cat}", "index": si + 1, "total": len(categories)})

        try:
            url = f"https://remotive.com/api/remote-jobs?category={cat}&limit=100"
            resp = requests.get(url, headers=_API_HEADERS, timeout=15)
            resp.raise_for_status()
            jobs = resp.json().get("jobs", [])
        except Exception as e:
            emit({"type": "error", "message": f"Remotive API error: {str(e)[:200]}"})
            continue

        emit({"type": "extract", "count": len(jobs)})

        for job in jobs:
            if len(all_posts) >= max_posts:
                break
            if not _is_fresh(job.get("publication_date", "")):
                continue
            job_url = job.get("url", "")
            title = job.get("title", "")
            company = job.get("company_name", "")
            location = job.get("candidate_required_location", "Remote")
            desc = re.sub(r'<[^>]+>', ' ', job.get("description", ""))[:500]
            tags = ", ".join(job.get("tags", []))
            if tags:
                desc += f"\nSkills: {tags}"
            salary = job.get("salary", "")
            if salary:
                desc += f"\nSalary: {salary}"

            _process_api_job(job_url, title, company, location, desc,
                             "Remotive", cat, dedup, all_posts, emit)

        time.sleep(random.uniform(0.5, 1))

    emit({"type": "done", "total": len(all_posts), "queries_searched": len(categories),
          "message": f"Remotive complete: {len(all_posts)} posts"})
    return all_posts


# ─── WeWorkRemotely RSS Scraper ───────────────────────────────────────────────

def scrape_wwr_rss(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape We Work Remotely via RSS feeds. No auth, no browser needed."""
    import xml.etree.ElementTree as ET

    all_posts = []
    dedup = DedupCache(conn)
    emit = _make_emit(on_event)

    feeds = [
        ("Programming", "https://weworkremotely.com/categories/remote-programming-jobs.rss"),
        ("DevOps/SysAdmin", "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss"),
    ]

    emit({"type": "info", "message": "Fetching WWR RSS feeds..."})

    for si, (cat_name, feed_url) in enumerate(feeds):
        if len(all_posts) >= max_posts:
            break
        emit({"type": "search", "query": f"WWR RSS: {cat_name}", "index": si + 1, "total": len(feeds)})

        try:
            resp = requests.get(feed_url, headers={**_API_HEADERS, "Accept": "application/rss+xml, application/xml, text/xml"}, timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception as e:
            emit({"type": "error", "message": f"WWR RSS error: {str(e)[:200]}"})
            continue

        items = root.findall(".//item")
        emit({"type": "extract", "count": len(items)})

        for item in items:
            if len(all_posts) >= max_posts:
                break
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            desc_raw = item.findtext("description", "")
            desc = re.sub(r'<[^>]+>', ' ', desc_raw)[:500]

            if not _is_fresh(pub_date):
                continue

            # WWR titles are often "Company: Role"
            parts = title.split(":", 1)
            company = parts[0].strip() if len(parts) > 1 else ""
            role_title = parts[1].strip() if len(parts) > 1 else title

            _process_api_job(link, role_title, company, "Remote", desc,
                             "WeWorkRemotely", cat_name, dedup, all_posts, emit)

    emit({"type": "done", "total": len(all_posts), "queries_searched": len(feeds),
          "message": f"WWR RSS complete: {len(all_posts)} posts"})
    return all_posts


# ─── Working Nomads Scraper ───────────────────────────────────────────────────

def scrape_workingnomads(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape Working Nomads via their JSON API."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = _make_emit(on_event)

    emit({"type": "info", "message": "Fetching Working Nomads API..."})
    emit({"type": "search", "query": "Working Nomads: development", "index": 1, "total": 1})

    try:
        url = "https://www.workingnomads.com/api/exposed_jobs/"
        resp = requests.get(url, headers=_API_HEADERS, timeout=15)
        resp.raise_for_status()
        jobs = resp.json()
    except Exception as e:
        emit({"type": "error", "message": f"Working Nomads API error: {str(e)[:200]}"})
        return all_posts

    emit({"type": "extract", "count": len(jobs)})

    for job in jobs:
        if len(all_posts) >= max_posts:
            break
        pub_date = job.get("pub_date", "")
        if not _is_fresh(pub_date):
            continue

        job_url = job.get("url", "")
        title = job.get("title", "")
        company = job.get("company_name", "")
        location = job.get("location", "Remote")
        desc = job.get("description", "")[:500]
        category = job.get("category_name", "")

        _process_api_job(job_url, title, company, location, desc,
                         "WorkingNomads", category, dedup, all_posts, emit)

    emit({"type": "done", "total": len(all_posts), "queries_searched": 1,
          "message": f"Working Nomads complete: {len(all_posts)} posts"})
    return all_posts


# ─── ATS Scrapers (Greenhouse + Lever + Ashby) ───────────────────────────────
# These ATS platforms expose FREE public JSON APIs for company job boards.
# One scraper per ATS, looping through a list of target companies.

# Top AI/ML companies by ATS platform (curated for relevance)
ATS_COMPANIES = {
    "greenhouse": [
        "anthropic", "stripe", "figma", "notion", "airbnb", "cloudflare",
        "databricks", "datadog", "discord", "duolingo", "gitlab",
        "hashicorp", "hubspot", "instacart", "lyft", "mongodb",
        "palantir", "pinterest", "plaid", "ramp", "reddit",
        "scale", "snorkelai", "weights-and-biases", "cohere",
        "anyscale", "langchain", "mistral", "huggingface",
        "replit", "vercel", "supabase", "neon",
    ],
    "lever": [
        "spotify", "meesho", "paytm",
    ],
    "ashby": [
        "ramp", "linear", "vercel",
    ],
}


def scrape_greenhouse(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape Greenhouse public job board APIs. No auth needed."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = _make_emit(on_event)

    companies = ATS_COMPANIES["greenhouse"]
    emit({"type": "info", "message": f"Scraping {len(companies)} Greenhouse company boards..."})

    for si, company in enumerate(companies):
        if len(all_posts) >= max_posts:
            break
        emit({"type": "search", "query": f"Greenhouse: {company}", "index": si + 1, "total": len(companies)})

        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
            resp = requests.get(url, headers=_API_HEADERS, timeout=10)
            if resp.status_code == 404:
                continue  # Company not on Greenhouse
            resp.raise_for_status()
            jobs = resp.json().get("jobs", [])
        except Exception as e:
            emit({"type": "error", "message": f"Greenhouse {company}: {str(e)[:100]}"})
            continue

        # Filter for AI/ML roles only
        ai_keywords = {"ai", "ml", "machine learning", "data scien", "nlp", "deep learning",
                        "llm", "genai", "generative", "computer vision", "python", "engineer"}
        matched = []
        for job in jobs:
            title_lower = job.get("title", "").lower()
            if any(kw in title_lower for kw in ai_keywords):
                # Check freshness
                updated = job.get("updated_at", "") or job.get("created_at", "")
                if _is_fresh(updated):
                    matched.append(job)

        if matched:
            emit({"type": "extract", "count": len(matched)})

        for job in matched:
            if len(all_posts) >= max_posts:
                break
            title = job.get("title", "")
            location = job.get("location", {}).get("name", "Remote") if isinstance(job.get("location"), dict) else str(job.get("location", "Remote"))
            job_url = job.get("absolute_url", "") or f"https://boards.greenhouse.io/{company}/jobs/{job.get('id', '')}"
            desc = re.sub(r'<[^>]+>', ' ', job.get("content", ""))[:500] if job.get("content") else ""

            _process_api_job(job_url, title, company.replace("-", " ").title(), location, desc,
                             "Greenhouse", company, dedup, all_posts, emit)

        time.sleep(random.uniform(0.3, 0.8))

    emit({"type": "done", "total": len(all_posts), "queries_searched": len(companies),
          "message": f"Greenhouse complete: {len(all_posts)} posts from {len(companies)} companies"})
    return all_posts


def scrape_lever(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape Lever public job board APIs. No auth needed."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = _make_emit(on_event)

    companies = ATS_COMPANIES["lever"]
    emit({"type": "info", "message": f"Scraping {len(companies)} Lever company boards..."})

    for si, company in enumerate(companies):
        if len(all_posts) >= max_posts:
            break
        emit({"type": "search", "query": f"Lever: {company}", "index": si + 1, "total": len(companies)})

        try:
            url = f"https://api.lever.co/v0/postings/{company}?mode=json"
            resp = requests.get(url, headers=_API_HEADERS, timeout=10)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            jobs = resp.json()
            if not isinstance(jobs, list):
                continue
        except Exception as e:
            emit({"type": "error", "message": f"Lever {company}: {str(e)[:100]}"})
            continue

        ai_keywords = {"ai", "ml", "machine learning", "data scien", "nlp", "deep learning",
                        "llm", "genai", "generative", "computer vision", "python", "engineer"}
        matched = []
        for job in jobs:
            title_lower = job.get("text", "").lower()
            if any(kw in title_lower for kw in ai_keywords):
                # Lever uses epoch milliseconds
                created_ms = job.get("createdAt", 0)
                if created_ms:
                    created = str(int(created_ms) // 1000)  # Convert ms to seconds
                else:
                    created = ""
                if _is_fresh(created):
                    matched.append(job)

        if matched:
            emit({"type": "extract", "count": len(matched)})

        for job in matched:
            if len(all_posts) >= max_posts:
                break
            title = job.get("text", "")
            location = job.get("categories", {}).get("location", "Remote") if isinstance(job.get("categories"), dict) else "Remote"
            job_url = job.get("hostedUrl", "") or job.get("applyUrl", "")
            desc_plain = job.get("descriptionPlain", "")[:500]

            _process_api_job(job_url, title, company.title(), location, desc_plain,
                             "Lever", company, dedup, all_posts, emit)

        time.sleep(random.uniform(0.3, 0.8))

    emit({"type": "done", "total": len(all_posts), "queries_searched": len(companies),
          "message": f"Lever complete: {len(all_posts)} posts from {len(companies)} companies"})
    return all_posts


def scrape_ashby(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape Ashby public job board APIs. No auth needed."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = _make_emit(on_event)

    companies = ATS_COMPANIES["ashby"]
    emit({"type": "info", "message": f"Scraping {len(companies)} Ashby company boards..."})

    for si, company in enumerate(companies):
        if len(all_posts) >= max_posts:
            break
        emit({"type": "search", "query": f"Ashby: {company}", "index": si + 1, "total": len(companies)})

        try:
            # Ashby API returns job boards — try both URL patterns
            url = f"https://api.ashbyhq.com/posting-api/job-board/{company}"
            resp = requests.get(url, headers=_API_HEADERS, timeout=10)
            if resp.status_code == 404:
                # Try alternate URL format
                url = f"https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
                resp = requests.post(url, json={"operationName": "ApiJobBoardWithTeams", "variables": {"organizationHostedJobsPageName": company}}, headers={**_API_HEADERS, "Content-Type": "application/json"}, timeout=10)
                if resp.status_code != 200:
                    continue
            resp.raise_for_status()
            data = resp.json()
            jobs = data.get("jobs", []) or data.get("data", {}).get("jobBoard", {}).get("jobPostings", [])
        except Exception as e:
            emit({"type": "error", "message": f"Ashby {company}: {str(e)[:100]}"})
            continue

        ai_keywords = {"ai", "ml", "machine learning", "data scien", "nlp", "deep learning",
                        "llm", "genai", "generative", "computer vision", "python", "engineer"}
        matched = [j for j in jobs if any(kw in j.get("title", "").lower() for kw in ai_keywords)]

        if matched:
            emit({"type": "extract", "count": len(matched)})

        for job in matched:
            if len(all_posts) >= max_posts:
                break
            title = job.get("title", "")
            location = job.get("location", "Remote")
            if isinstance(location, dict):
                location = location.get("name", "Remote")
            job_url = job.get("jobUrl", "") or job.get("applyUrl", "")
            desc = job.get("descriptionPlain", "")[:500] if job.get("descriptionPlain") else ""

            _process_api_job(job_url, title, company.title(), location, desc,
                             "Ashby", company, dedup, all_posts, emit)

        time.sleep(random.uniform(0.3, 0.8))

    emit({"type": "done", "total": len(all_posts), "queries_searched": len(companies),
          "message": f"Ashby complete: {len(all_posts)} posts from {len(companies)} companies"})
    return all_posts


# ─── JobSpy Wrapper (LinkedIn + Indeed + Google + ZipRecruiter + Bayt) ────────

def scrape_jobspy(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape multiple platforms via python-jobspy library."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = _make_emit(on_event)

    try:
        from jobspy import scrape_jobs
    except ImportError:
        emit({"type": "error", "message": "python-jobspy not installed. Run: pip install python-jobspy"})
        return all_posts

    search_terms = [
        "AI Engineer remote",
        "Machine Learning Engineer remote",
        "GenAI Engineer",
        "LLM Engineer",
    ]

    emit({"type": "info", "message": "Starting JobSpy multi-platform scraper..."})

    for si, term in enumerate(search_terms):
        if len(all_posts) >= max_posts:
            break
        emit({"type": "search", "query": f"JobSpy: {term}", "index": si + 1, "total": len(search_terms)})

        try:
            jobs_df = scrape_jobs(
                site_name=["indeed", "google"],
                search_term=term,
                location="remote",
                results_wanted=min(30, max_posts - len(all_posts)),
                hours_old=24 * MAX_JOB_AGE_DAYS,
                country_indeed="worldwide",
            )
        except Exception as e:
            emit({"type": "error", "message": f"JobSpy error: {str(e)[:200]}"})
            continue

        if jobs_df is None or jobs_df.empty:
            emit({"type": "extract", "count": 0})
            continue

        emit({"type": "extract", "count": len(jobs_df)})

        for _, row in jobs_df.iterrows():
            if len(all_posts) >= max_posts:
                break
            job_url = str(row.get("job_url", ""))
            title = str(row.get("title", ""))
            company = str(row.get("company", ""))
            location = str(row.get("location", "Remote"))
            desc = str(row.get("description", ""))[:500]
            site = str(row.get("site", "jobspy"))

            _process_api_job(job_url, title, company, location, desc,
                             f"JobSpy/{site}", term, dedup, all_posts, emit)

        time.sleep(random.uniform(1, 2))

    emit({"type": "done", "total": len(all_posts), "queries_searched": len(search_terms),
          "message": f"JobSpy complete: {len(all_posts)} posts"})
    return all_posts
