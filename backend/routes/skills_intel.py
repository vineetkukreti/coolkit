"""Skills Intelligence API routes."""

import threading
from fastapi import APIRouter
from pydantic import BaseModel
from db import init_db

router = APIRouter()

_local = threading.local()


def _get_db():
    # Honor an explicitly-set connection (used directly by tests).
    override = getattr(_local, 'conn', None)
    if override is not None:
        return override
    # Otherwise keep one connection per user PER THREAD. Thread-local keeps each
    # connection confined to one thread (SQLite-safe); keying by user id stops a
    # pooled thread from serving user B with the connection it opened for user A.
    from db import current_user_id
    uid = current_user_id.get()
    cache = getattr(_local, 'by_user', None)
    if cache is None:
        cache = _local.by_user = {}
    conn = cache.get(uid)
    if conn is None:
        conn = cache[uid] = init_db()
    return conn


class AnalyzeRequest(BaseModel):
    use_llm: bool = False
    llm_sample_size: int = 100


@router.get("/api/skills/dashboard")
def api_skills_dashboard():
    """Main skills intelligence dashboard data."""
    from services.skills_intel import get_dashboard_data
    return get_dashboard_data(_get_db())


@router.post("/api/skills/analyze")
def api_skills_analyze(req: AnalyzeRequest = None):
    """Trigger background skills analysis."""
    from services.skills_intel import start_analysis
    if req is None:
        req = AnalyzeRequest()
    return start_analysis(use_llm=req.use_llm, llm_sample=req.llm_sample_size)


@router.get("/api/skills/analysis-status")
def api_skills_analyze_status():
    """Poll analysis progress."""
    from services.skills_intel import get_analysis_status
    return get_analysis_status()


@router.get("/api/skills/gaps")
def api_skills_gaps():
    """Resume gap analysis against market demands."""
    from services.skills_intel import compute_gap_analysis
    return compute_gap_analysis(_get_db())


@router.get("/api/skills/trends")
def api_skills_trends():
    """Get cached trending tools/tech."""
    from services.skills_intel import get_trend_data
    return get_trend_data()


@router.post("/api/skills/trends/refresh")
def api_skills_trends_refresh():
    """Re-fetch trends from Gemini."""
    from services.skills_intel import refresh_trends
    return refresh_trends()


@router.get("/api/skills/news")
def api_skills_news():
    """Get cached industry news."""
    from services.skills_intel import get_news_data
    return get_news_data()


@router.post("/api/skills/news/refresh")
def api_skills_news_refresh():
    """Re-fetch news from Gemini."""
    from services.skills_intel import refresh_news
    return refresh_news()
