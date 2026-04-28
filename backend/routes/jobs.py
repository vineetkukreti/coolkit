"""Job search, apply/skip, and application history routes."""

import time
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter
from pydantic import BaseModel

from config import RESUME_SKILLS
from db import init_db, log_application, get_applied_urls, get_applications, get_application_stats, get_today_quota

router = APIRouter()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ─── Models ──────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    keywords: str = "healthcare AI engineer"
    location: str = "India"
    platforms: list[str] = ["linkedin", "naukri", "wellfound"]
    max_jobs: int = 10


class ApplyRequest(BaseModel):
    url: str
    title: str
    company: str
    location: str
    platform: str


# ─── Scrapers ────────────────────────────────────────────────────────────────

def _fetch(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except Exception:
        return None


def _match_score(title: str, company: str) -> tuple[int, list[str]]:
    text = f"{title} {company}".lower()
    score = 0
    matched = []
    for skill, weight in RESUME_SKILLS.items():
        if skill in text:
            score += weight
            matched.append(skill)
    return score, matched


def scrape_linkedin(keywords: str, location: str, max_jobs: int) -> list[dict]:
    jobs = []
    pages = (max_jobs // 25) + 1
    for page in range(pages):
        if len(jobs) >= max_jobs:
            break
        start = page * 25
        url = (
            f"https://www.linkedin.com/jobs/search"
            f"?keywords={quote_plus(keywords)}"
            f"&location={quote_plus(location)}"
            f"&start={start}&f_TPR=r604800"
        )
        soup = _fetch(url)
        if not soup:
            break
        cards = soup.select("div.base-card, li.result-card, div.job-search-card")
        if not cards:
            break
        for card in cards:
            if len(jobs) >= max_jobs:
                break
            title_el = card.select_one("h3.base-search-card__title, h3.job-search-card__title, h3")
            company_el = card.select_one("h4.base-search-card__subtitle, a.hidden-nested-link, h4")
            loc_el = card.select_one("span.job-search-card__location, span.base-search-card__metadata")
            link_el = card.select_one("a[href*='/jobs/view'], a.base-card__full-link")
            date_el = card.select_one("time")
            title = title_el.get_text(strip=True) if title_el else ""
            company = company_el.get_text(strip=True) if company_el else ""
            loc = loc_el.get_text(strip=True) if loc_el else ""
            href = link_el["href"].split("?")[0] if link_el and link_el.get("href") else ""
            posted = date_el.get("datetime", "") if date_el else ""
            if title:
                score, matched = _match_score(title, company)
                jobs.append({
                    "title": title, "company": company, "location": loc,
                    "url": href, "platform": "LinkedIn", "match_score": score,
                    "matched_skills": matched, "posted": posted,
                })
        time.sleep(1)
    return jobs


def scrape_naukri(keywords: str, location: str, max_jobs: int) -> list[dict]:
    kw = keywords.replace(" ", "-")
    loc = location.lower().replace(" ", "-")
    return [{
        "title": f"Search: {keywords}",
        "company": "Open on Naukri.com",
        "location": location,
        "url": f"https://www.naukri.com/{kw}-jobs-in-{loc}",
        "platform": "Naukri", "match_score": 0,
        "matched_skills": [], "is_search_link": True,
    }]


def scrape_wellfound(keywords: str, location: str, max_jobs: int) -> list[dict]:
    return [{
        "title": f"Search: {keywords}",
        "company": "Open on Wellfound",
        "location": location,
        "url": f"https://wellfound.com/jobs?query={quote_plus(keywords)}&location={quote_plus(location)}",
        "platform": "Wellfound", "match_score": 0,
        "matched_skills": [], "is_search_link": True,
    }]


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/api/search")
def search_jobs(req: SearchRequest):
    all_jobs = []
    if "linkedin" in req.platforms:
        all_jobs.extend(scrape_linkedin(req.keywords, req.location, req.max_jobs))
    if "naukri" in req.platforms:
        all_jobs.extend(scrape_naukri(req.keywords, req.location, req.max_jobs))
    if "wellfound" in req.platforms:
        all_jobs.extend(scrape_wellfound(req.keywords, req.location, req.max_jobs))
    seen = set()
    unique = []
    for job in all_jobs:
        key = job["url"] or f"{job['title']}|{job['company']}"
        if key not in seen:
            seen.add(key)
            unique.append(job)
    unique.sort(key=lambda j: j.get("match_score", 0), reverse=True)
    return {"jobs": unique, "total": len(unique)}


@router.post("/api/apply")
def mark_applied(req: ApplyRequest):
    conn = init_db()
    log_application(
        conn, req.platform, req.url, req.title, req.company, req.location,
        status="applied", apply_method="manual",
    )
    return {"status": "ok", "message": f"Logged application to {req.company}"}


@router.post("/api/skip")
def mark_skipped(req: ApplyRequest):
    conn = init_db()
    log_application(
        conn, req.platform, req.url, req.title, req.company, req.location,
        status="skipped", apply_method="manual",
    )
    return {"status": "ok"}


@router.get("/api/applications")
def api_get_applications(status: str | None = None):
    conn = init_db()
    apps = get_applications(conn, status=status)
    return {"applications": apps, "total": len(apps)}


@router.get("/api/stats")
def get_apply_stats():
    conn = init_db()
    return get_application_stats(conn)


@router.get("/api/applications/quota")
def api_get_quota():
    conn = init_db()
    return get_today_quota(conn)


@router.get("/api/applications/export")
def api_export_applications():
    """Export applications log as CSV file."""
    import os
    from fastapi.responses import FileResponse
    from services.logger import LOG_FILE, _ensure_log
    _ensure_log()
    if not os.path.exists(LOG_FILE):
        return {"error": "No export file found"}
    return FileResponse(LOG_FILE, media_type="text/csv", filename="applications_log.csv")
