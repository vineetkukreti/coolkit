"""AI tools, ATS scanner, follow-up, liveness, and analytics routes."""

import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

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
        print(f"Error in /api/tools/evaluate: {e}")
        raise HTTPException(status_code=500, detail="Job evaluation failed. Please try again.")


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
        print(f"Error in /api/tools/outreach: {e}")
        raise HTTPException(status_code=500, detail="Outreach generation failed. Please try again.")


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
        print(f"Error in /api/tools/deep-dive: {e}")
        raise HTTPException(status_code=500, detail="Company research failed. Please try again.")


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
        print(f"Error in /api/tools/tailor-cv: {e}")
        raise HTTPException(status_code=500, detail="CV tailoring failed. Please try again.")


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
        print(f"Error in /api/tools/interview-prep: {e}")
        raise HTTPException(status_code=500, detail="Interview prep generation failed. Please try again.")


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
    """List all configured resume variants with full details."""
    from services.resume_selector import RESUME_VARIANTS
    result = []
    for name, variant in RESUME_VARIANTS.items():
        path = Path(variant["path"])
        result.append({
            "name": name,
            "path": str(path),
            "description": variant["description"],
            "keywords": variant["keywords"],
            "weight": variant.get("weight", 1.0),
            "exists": path.exists(),
            "size_kb": round(path.stat().st_size / 1024) if path.exists() else 0,
        })
    return {"variants": result}


@router.post("/api/resumes/variants/{variant_name}/upload")
def api_upload_variant(variant_name: str, file: UploadFile = File(...)):
    """Upload a PDF for a specific resume variant."""
    from services.resume_selector import RESUME_VARIANTS
    if variant_name not in RESUME_VARIANTS:
        raise HTTPException(status_code=404, detail=f"Unknown variant: {variant_name}")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    # Always save as resume.pdf — same name for all variants
    dest = Path(f"assets/resumes/{variant_name}/resume.pdf")
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = file.file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Max 10MB.")
    dest.write_bytes(content)
    return {
        "status": "ok",
        "variant": variant_name,
        "filename": dest.name,
        "size_kb": round(len(content) / 1024),
    }


class TestSelectionRequest(BaseModel):
    role: str = ""
    content: str = ""
    domain_relevance: str = ""
    company: str = ""


@router.post("/api/resumes/test-selection")
def api_test_selection(req: TestSelectionRequest):
    """Test which resume variant would be selected for given job info."""
    from services.resume_selector import RESUME_VARIANTS, select_resume
    text = f"{req.role} {req.content} {req.company}".lower()

    # Compute scores for transparency
    scores = {}
    for name, variant in RESUME_VARIANTS.items():
        if name == "default":
            continue
        hits = sum(1 for kw in variant["keywords"] if kw in text)
        score = hits * variant.get("weight", 1.0)
        if name == "healthcare-ai" and req.domain_relevance == "High":
            score += 5.0
        elif name == "healthcare-ai" and req.domain_relevance == "Medium":
            score += 2.0
        scores[name] = {"score": score, "hits": hits}

    selected = select_resume(
        role=req.role, content=req.content,
        domain_relevance=req.domain_relevance, company=req.company,
    )
    selected_name = next(
        (n for n, v in RESUME_VARIANTS.items() if v["path"] == selected),
        "default",
    )
    return {"selected": selected_name, "path": selected, "scores": scores}


@router.get("/api/dashboard/quality")
def api_dashboard_quality():
    """Get comprehensive application quality dashboard data."""
    from services.quality_dashboard import get_dashboard_data
    conn = _get_db()
    return get_dashboard_data(conn)


@router.get("/api/email/ab-stats")
def api_email_ab_stats():
    """Get A/B email variant performance statistics."""
    from services.email_ab_test import get_ab_stats
    conn = _get_db()
    return get_ab_stats(conn)


@router.post("/api/company/scan")
def api_company_scan(req: dict):
    """Scan a company for health signals."""
    from services.company_signals import scan_company
    company = req.get("company", "")
    if not company:
        raise HTTPException(status_code=400, detail="company required")
    conn = _get_db()
    return scan_company(company, conn=conn)


@router.post("/api/company/connections")
def api_company_connections(req: dict):
    """Find existing connections at a company (referral detection)."""
    from services.referral_detector import find_connections
    company = req.get("company", "")
    if not company:
        raise HTTPException(status_code=400, detail="company required")
    conn = _get_db()
    return find_connections(conn, company)


@router.post("/api/followup/auto-send")
def api_followup_auto_send():
    from services.email_service import start_auto_followup
    return start_auto_followup()

@router.post("/api/followup/preview/{outreach_id}")
def api_followup_preview(outreach_id: int):
    from services.email_service import preview_followup
    return preview_followup(outreach_id)

@router.get("/api/followup/worker-status")
def api_followup_worker_status():
    from services.email_service import get_followup_worker_status
    return get_followup_worker_status()

@router.post("/api/followup/worker-stop")
def api_followup_worker_stop():
    from services.email_service import stop_followup_worker
    return stop_followup_worker()


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
