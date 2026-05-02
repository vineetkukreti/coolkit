"""Quality Gate — pre-apply scoring to prevent low-quality applications."""

import sqlite3
from datetime import datetime

try:
    from config import RESUME_SKILLS, PROFILE, TARGET_ROLES
except ImportError:
    RESUME_SKILLS = {}
    PROFILE = {}
    TARGET_ROLES = []

try:
    from services.ats_scorer import compute_ats_score
except ImportError:
    compute_ats_score = None


# Quality tiers with minimum thresholds
QUALITY_TIERS = {
    "premium": {"min_smart": 7.0, "min_ats": 65, "label": "Premium", "action": "Personalized email + tailored resume", "color": "success"},
    "standard": {"min_smart": 5.0, "min_ats": 45, "label": "Standard", "action": "Standard email + generic resume", "color": "info"},
    "basic": {"min_smart": 3.5, "min_ats": 30, "label": "Basic", "action": "Template email only", "color": "warning"},
    "skip": {"min_smart": 0, "min_ats": 0, "label": "Skip", "action": "Do not apply", "color": "danger"},
}


def gate_check(post_id: int = None, jd_text: str = None, smart_score: float = None, conn: sqlite3.Connection = None) -> dict:
    """Run quality gate check before applying to a job.

    Returns tier, scores, and recommendation.
    Can work from post_id (DB lookup) or raw jd_text + smart_score.
    """
    # Get data from DB if post_id provided
    content = jd_text or ""
    role = ""
    company = ""
    location = ""

    if post_id and conn:
        row = conn.execute(
            "SELECT p.content, p.smart_score, p.is_live, j.role, j.company, j.location, j.experience "
            "FROM posts p LEFT JOIN jobs j ON j.post_id = p.id WHERE p.id = ?",
            (post_id,)
        ).fetchone()
        if row:
            row = dict(row)
            content = row.get("content", "") or ""
            smart_score = row.get("smart_score") if smart_score is None else smart_score
            role = row.get("role", "") or ""
            company = row.get("company", "") or ""
            location = row.get("location", "") or ""

    # Compute ATS score if we have content
    ats_result = None
    ats_score = 0
    if content and compute_ats_score:
        ats_result = compute_ats_score(content)
        ats_score = ats_result.get("ats_score", 0)

    smart = smart_score or 0

    # Determine tier
    if smart >= QUALITY_TIERS["premium"]["min_smart"] and ats_score >= QUALITY_TIERS["premium"]["min_ats"]:
        tier = "premium"
    elif smart >= QUALITY_TIERS["standard"]["min_smart"] and ats_score >= QUALITY_TIERS["standard"]["min_ats"]:
        tier = "standard"
    elif smart >= QUALITY_TIERS["basic"]["min_smart"]:
        tier = "basic"
    else:
        tier = "skip"

    tier_info = QUALITY_TIERS[tier]

    # Build warnings
    warnings = []
    if smart < 3.5:
        warnings.append("Smart score below minimum threshold (3.5)")
    if ats_score < 30 and content:
        warnings.append("Very low ATS keyword match — resume likely filtered out")
    if ats_score >= 30 and ats_score < 50:
        warnings.append("Moderate ATS match — consider tailoring resume")
    if not content:
        warnings.append("No job description available for ATS scoring")

    # Build recommendation
    if tier == "premium":
        recommendation = "Strong match! Apply with personalized email and tailored resume."
    elif tier == "standard":
        recommendation = "Good match. Apply with standard approach."
    elif tier == "basic":
        recommendation = "Weak match. Consider if this role truly fits your goals."
    else:
        recommendation = "Not recommended. Score too low — save your time for better matches."

    return {
        "tier": tier,
        "label": tier_info["label"],
        "action": tier_info["action"],
        "color": tier_info["color"],
        "smart_score": round(smart, 1),
        "ats_score": ats_score,
        "recommendation": recommendation,
        "warnings": warnings,
        "should_apply": tier != "skip",
        "ats_details": ats_result,
        "role": role,
        "company": company,
        "location": location,
    }


def batch_gate_check(conn: sqlite3.Connection, limit: int = 50) -> dict:
    """Run quality gate on top unapplied jobs."""
    rows = conn.execute(
        """SELECT p.id, p.content, p.smart_score, p.is_live, j.role, j.company, j.location
           FROM posts p
           LEFT JOIN jobs j ON j.post_id = p.id
           WHERE p.is_hiring = 1
             AND p.id NOT IN (SELECT post_id FROM applications WHERE post_id IS NOT NULL)
           ORDER BY p.smart_score DESC NULLS LAST
           LIMIT ?""",
        (limit,)
    ).fetchall()

    results = []
    tier_counts = {"premium": 0, "standard": 0, "basic": 0, "skip": 0}

    for row in rows:
        row = dict(row)
        result = gate_check(
            jd_text=row.get("content", ""),
            smart_score=row.get("smart_score"),
        )
        result["post_id"] = row["id"]
        result["role"] = row.get("role", "")
        result["company"] = row.get("company", "")
        result["location"] = row.get("location", "")
        results.append(result)
        tier_counts[result["tier"]] += 1

    return {
        "total": len(results),
        "tier_breakdown": tier_counts,
        "jobs": results,
    }
