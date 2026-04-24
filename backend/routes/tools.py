"""AI tools, ATS scanner, follow-up, liveness, and analytics routes."""

import threading

from fastapi import APIRouter, HTTPException

from db import init_db

router = APIRouter()

# ───────────────────────────────────────────────
# Thread-local DB connection
# ───────────────────────────────────────────────
_local = threading.local()


def _get_db():
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = init_db()
    return _local.conn


# ───────────────────────────────────────────────
# AI Tools endpoints
# ───────────────────────────────────────────────

@router.post("/api/tools/evaluate")
def api_tools_evaluate(req: dict):
    """Evaluate a job posting with 7-block analysis."""
    from services.ai_tools import evaluate_job
    jd_text = req.get("jd_text", "")
    if not jd_text:
        raise HTTPException(status_code=400, detail="jd_text required")
    try:
        return evaluate_job(jd_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:300])


@router.post("/api/tools/outreach")
def api_tools_outreach(req: dict):
    """Generate personalized cold outreach messages."""
    from services.ai_tools import generate_outreach
    company = req.get("company", "")
    role = req.get("role", "")
    if not company:
        raise HTTPException(status_code=400, detail="company required")
    try:
        return generate_outreach(
            company=company,
            role=role,
            recruiter_name=req.get("recruiter_name", ""),
            context=req.get("context", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:300])


@router.post("/api/tools/deep-dive")
def api_tools_deep_dive(req: dict):
    """Deep research a company before outreach."""
    from services.ai_tools import deep_dive_company
    company = req.get("company", "")
    if not company:
        raise HTTPException(status_code=400, detail="company required")
    try:
        return deep_dive_company(company, req.get("role", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:300])


@router.post("/api/tools/tailor-cv")
def api_tools_tailor_cv(req: dict):
    """Generate ATS-optimized CV tailored to a JD."""
    from services.ai_tools import tailor_cv
    jd_text = req.get("jd_text", "")
    if not jd_text:
        raise HTTPException(status_code=400, detail="jd_text required")
    try:
        return tailor_cv(jd_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:300])


@router.post("/api/tools/interview-prep")
def api_tools_interview_prep(req: dict):
    """Generate interview prep for a company."""
    from services.ai_tools import interview_prep
    company = req.get("company", "")
    role = req.get("role", "")
    if not company:
        raise HTTPException(status_code=400, detail="company required")
    try:
        return interview_prep(company, role)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:300])


# ───────────────────────────────────────────────
# ATS Scanner endpoints
# ───────────────────────────────────────────────

@router.get("/api/ats/companies")
def api_ats_companies():
    """Return tracked companies from portals.yml."""
    try:
        import yaml
        with open("config/portals.yml") as f:
            config = yaml.safe_load(f)
        companies = config.get("tracked_companies", [])
        return {"companies": [{"name": c["name"], "enabled": c.get("enabled", True),
                               "notes": c.get("notes", "")} for c in companies],
                "total": len(companies)}
    except FileNotFoundError:
        return {"companies": [], "total": 0, "error": "portals.yml not found"}


@router.post("/api/ats/scan")
def api_ats_scan():
    """Run ATS API scan for healthcare AI jobs."""
    from services.ats_scanner import scan_all
    from db import insert_posts as _insert_posts

    conn = _get_db()
    results = []

    def on_event(evt):
        results.append(evt)

    try:
        jobs = scan_all(conn=conn, on_event=on_event)
        if jobs:
            inserted, skipped = _insert_posts(conn, jobs)
            return {"status": "done", "total_found": len(jobs), "inserted": inserted,
                    "skipped": skipped, "jobs": jobs[:50]}
        return {"status": "done", "total_found": 0, "inserted": 0, "skipped": 0, "jobs": []}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)[:300]}


# ───────────────────────────────────────────────
# Follow-up endpoints
# ───────────────────────────────────────────────

@router.get("/api/followup/status")
def api_followup_status():
    """Get follow-up urgency status for all sent emails."""
    from services.followup_cadence import analyze_followups
    conn = _get_db()
    return analyze_followups(conn)


@router.post("/api/followup/record")
def api_followup_record(req: dict):
    """Record a follow-up sent for an outreach entry."""
    from services.followup_cadence import record_followup
    outreach_id = req.get("outreach_id")
    if not outreach_id:
        raise HTTPException(status_code=400, detail="outreach_id required")
    conn = _get_db()
    return record_followup(conn, outreach_id)


# ───────────────────────────────────────────────
# Liveness endpoints
# ───────────────────────────────────────────────

@router.post("/api/liveness/check")
def api_liveness_check(req: dict):
    """Check if a job URL is still active."""
    from services.liveness import check_url_liveness, check_urls_batch
    url = req.get("url")
    urls = req.get("urls", [])
    if url:
        return check_url_liveness(url)
    elif urls:
        return {"results": check_urls_batch(urls)}
    raise HTTPException(status_code=400, detail="url or urls required")


@router.post("/api/liveness/scan")
def api_liveness_scan():
    """Batch check liveness of posts in DB."""
    from services.liveness import check_and_update_db
    conn = _get_db()
    return check_and_update_db(conn)


# ───────────────────────────────────────────────
# Analytics endpoints
# ───────────────────────────────────────────────

@router.get("/api/analytics/patterns")
def api_analytics_patterns():
    """Get email outreach pattern analysis with recommendations."""
    from services.pattern_analysis import analyze_patterns
    conn = _get_db()
    return analyze_patterns(conn)


@router.get("/api/analytics/conversion")
def api_analytics_conversion():
    """Get conversion rates per role and domain."""
    from services.pattern_analysis import get_conversion_rates
    conn = _get_db()
    return get_conversion_rates(conn)


# ───────────────────────────────────────────────
# Smart Filter endpoints
# ───────────────────────────────────────────────

@router.post("/api/smart-filter/score")
def api_smart_filter_score(req: dict):
    """Score a single job post by ID or content."""
    from services.smart_filter import score_and_update, score_job
    post_id = req.get("post_id")
    if post_id:
        conn = _get_db()
        return score_and_update(conn, post_id)
    # Score raw content
    return score_job(
        content=req.get("content", ""),
        role=req.get("role", ""),
        company=req.get("company", ""),
        location=req.get("location", ""),
        experience=req.get("experience", ""),
        domain_relevance=req.get("domain_relevance", ""),
        fit_score=req.get("fit_score"),
    )


@router.post("/api/smart-filter/score-all")
def api_smart_filter_score_all(req: dict = None):
    """Score all unscored hiring posts in the database."""
    from services.smart_filter import score_all_unscored
    conn = _get_db()
    limit = (req or {}).get("limit", 500)
    return score_all_unscored(conn, limit=limit)


@router.get("/api/smart-filter/stats")
def api_smart_filter_stats():
    """Get smart scoring statistics."""
    from services.smart_filter import get_filter_stats
    conn = _get_db()
    return get_filter_stats(conn)


@router.get("/api/smart-filter/top")
def api_smart_filter_top():
    """Get top-scoring unapplied jobs."""
    from services.smart_filter import filter_unapplied
    conn = _get_db()
    jobs = filter_unapplied(conn, threshold=3.5, limit=50)
    return {"jobs": jobs, "total": len(jobs)}


# ───────────────────────────────────────────────
# Resume variant endpoints
# ───────────────────────────────────────────────

@router.get("/api/resumes/variants")
def api_resume_variants():
    """List all configured resume variants."""
    from services.resume_selector import list_variants
    return {"variants": list_variants()}


@router.post("/api/company/scan")
def api_company_scan(req: dict):
    """Scan a company for health signals."""
    from services.company_signals import scan_company
    company = req.get("company", "")
    if not company:
        raise HTTPException(status_code=400, detail="company required")
    conn = _get_db()
    return scan_company(company, conn=conn)


@router.post("/api/resumes/select")
def api_resume_select(req: dict):
    """Select the best resume for a job."""
    from services.resume_selector import select_resume
    return {
        "selected": select_resume(
            role=req.get("role", ""),
            content=req.get("content", ""),
            domain_relevance=req.get("domain_relevance", ""),
            company=req.get("company", ""),
        )
    }
