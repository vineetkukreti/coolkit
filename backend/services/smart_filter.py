"""
Smart Filter — Intelligent scoring layer between scraping and auto-apply.

Scores scraped jobs on 6 weighted dimensions before they reach the auto-apply engine.
Only jobs above the threshold get applied to, replacing spray-and-pray with precision targeting.

Usage:
    from services.smart_filter import score_job, filter_unapplied, get_filter_stats

    # Score a single job
    result = score_job(content, role, company, location, experience, domain_relevance, fit_score)
    # result = {"smart_score": 7.2, "verdict": "APPLY", "breakdown": {...}}

    # Filter unapplied jobs (for orchestrator integration)
    good_jobs = filter_unapplied(conn, threshold=5.0, limit=100)
"""

import re
import json
import sqlite3
import os
from datetime import datetime

from config import RESUME_SKILLS, DOMAIN_KEYWORDS, TARGET_ROLES, PROFILE


# ─── Scoring Weights ────────────────────────────────────────────────────────

WEIGHTS = {
    "role_match":       0.25,  # How well the role title matches target roles
    "skill_match":      0.25,  # How many resume skills appear in the JD
    "domain_relevance": 0.20,  # Healthcare/clinical domain alignment
    "experience_fit":   0.15,  # Experience level appropriateness (2yr)
    "quality_signals":  0.10,  # JD quality, company signals, specificity
    "location_fit":     0.05,  # Remote-friendly, India-based, relocation-ok
}

# ─── Thresholds ──────────────────────────────────────────────────────────────

APPLY_THRESHOLD = 5.0       # Score >= 5.0 → auto-apply
CONSIDER_THRESHOLD = 3.5    # 3.5-5.0 → queue for manual review
SKIP_THRESHOLD = 3.5        # < 3.5 → skip entirely


# ─── Dimension Scorers ──────────────────────────────────────────────────────

def _score_role_match(role: str, content: str) -> tuple[float, str]:
    """Score how well the role matches target roles. Returns (0-10, reason)."""
    if not role:
        return 3.0, "no role extracted"

    role_lower = role.lower()
    content_lower = (content or "").lower()

    # Exact target role match
    for target in TARGET_ROLES:
        if target.lower() in role_lower:
            return 10.0, f"exact match: {target}"

    # Partial matches
    ai_terms = ["ai", "artificial intelligence", "machine learning", "ml", "deep learning"]
    llm_terms = ["llm", "genai", "generative ai", "large language model", "nlp"]
    agent_terms = ["agentic", "agent", "autonomous", "multi-agent"]

    if any(t in role_lower for t in agent_terms):
        return 9.0, "agentic AI role"
    if any(t in role_lower for t in llm_terms):
        return 8.5, "LLM/GenAI role"
    if any(t in role_lower for t in ai_terms):
        return 8.0, "AI/ML role"
    if "python" in role_lower and any(t in content_lower for t in ai_terms):
        return 6.0, "Python role with AI in description"
    if "data scientist" in role_lower:
        return 5.0, "data science (adjacent)"
    if "data engineer" in role_lower:
        return 4.0, "data engineering (less relevant)"

    return 2.0, f"unmatched role: {role[:40]}"


def _score_skill_match(content: str) -> tuple[float, str]:
    """Score how many resume skills appear in the job content."""
    if not content:
        return 3.0, "no content to match"

    content_lower = content.lower()
    total_weight = sum(RESUME_SKILLS.values())
    matched_weight = 0
    matched_skills = []

    for skill, weight in RESUME_SKILLS.items():
        if skill.lower() in content_lower:
            matched_weight += weight
            matched_skills.append(skill)

    if total_weight == 0:
        return 5.0, "no skills configured"

    pct = matched_weight / total_weight
    score = min(10.0, pct * 15)  # Scale so ~66% match = 10

    top_3 = matched_skills[:3]
    return round(score, 1), f"{len(matched_skills)} skills matched ({', '.join(top_3)}{'...' if len(matched_skills) > 3 else ''})"


def _score_domain_relevance(domain_relevance: str, content: str) -> tuple[float, str]:
    """Score healthcare/clinical domain alignment."""
    if domain_relevance == "High":
        return 10.0, "high domain relevance (healthcare/clinical)"

    content_lower = (content or "").lower()
    domain_hits = sum(1 for kw in DOMAIN_KEYWORDS if kw in content_lower)

    if domain_hits >= 5 or domain_relevance == "High":
        return 10.0, f"strong domain signals ({domain_hits} keywords)"
    elif domain_hits >= 3 or domain_relevance == "Medium":
        return 7.0, f"moderate domain signals ({domain_hits} keywords)"
    elif domain_hits >= 1:
        return 4.0, f"weak domain signals ({domain_hits} keywords)"
    else:
        return 2.0, "no healthcare/clinical domain signals"


def _score_experience_fit(experience: str, content: str) -> tuple[float, str]:
    """Score whether the experience requirement fits 2 years."""
    if not experience:
        # Try to extract from content
        content_lower = (content or "").lower()
        exp_match = re.search(r'(\d+)\s*[-\u2013to]+\s*(\d+)\s*(?:years?|yrs?)', content_lower)
        if not exp_match:
            exp_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)', content_lower)
            if exp_match:
                min_yr = int(exp_match.group(1))
                max_yr = min_yr + 2
            else:
                return 6.0, "experience not specified (neutral)"
        else:
            min_yr = int(exp_match.group(1))
            max_yr = int(exp_match.group(2))
    else:
        exp_lower = experience.lower()
        if "fresher" in exp_lower:
            return 4.0, "fresher-only (may be underleveled)"
        range_match = re.search(r'(\d+)\s*[-\u2013to]+\s*(\d+)', exp_lower)
        if range_match:
            min_yr, max_yr = int(range_match.group(1)), int(range_match.group(2))
        else:
            single_match = re.search(r'(\d+)', exp_lower)
            if single_match:
                min_yr = int(single_match.group(1))
                max_yr = min_yr + 2
            else:
                return 6.0, "experience format unclear"

    candidate_years = PROFILE.get("experience_years", 2)

    # Sweet spot: candidate years within the range
    if min_yr <= candidate_years <= max_yr:
        return 10.0, f"perfect fit ({min_yr}-{max_yr}yr range, have {candidate_years}yr)"
    # Slightly over-leveled (within 1 year)
    elif candidate_years < min_yr and (min_yr - candidate_years) <= 1:
        return 7.0, f"stretch role ({min_yr}-{max_yr}yr, have {candidate_years}yr - can frame up)"
    # Under-leveled significantly
    elif candidate_years < min_yr:
        gap = min_yr - candidate_years
        if gap <= 3:
            return 4.0, f"over-leveled by {gap}yr ({min_yr}-{max_yr}yr) — worth trying"
        return 2.0, f"too senior ({min_yr}-{max_yr}yr needed, have {candidate_years}yr)"
    # Over-qualified
    elif candidate_years > max_yr:
        return 5.0, f"overqualified ({min_yr}-{max_yr}yr, have {candidate_years}yr)"

    return 6.0, "experience fit unclear"


def _score_quality_signals(content: str) -> tuple[float, str]:
    """Score JD quality and company signals."""
    if not content:
        return 3.0, "no content to evaluate"

    content_lower = content.lower()
    signals = []
    score = 5.0  # Start neutral

    # Positive signals
    if any(w in content_lower for w in ["tech stack", "architecture", "system design", "pipeline"]):
        score += 1.0
        signals.append("+technical depth")
    if any(w in content_lower for w in ["equity", "stock", "rsu", "esop"]):
        score += 0.5
        signals.append("+equity")
    if any(w in content_lower for w in ["team of", "engineers", "scientists", "researchers"]):
        score += 0.5
        signals.append("+team mentioned")
    if len(content) > 500:
        score += 0.5
        signals.append("+detailed JD")
    if any(w in content_lower for w in ["series a", "series b", "series c", "ipo", "funded"]):
        score += 0.5
        signals.append("+funded company")

    # Negative signals
    if any(w in content_lower for w in ["unpaid", "volunteer", "intern only"]):
        score -= 3.0
        signals.append("-unpaid/volunteer")
    if len(content) < 100:
        score -= 1.0
        signals.append("-very short JD")
    if any(w in content_lower for w in ["must be us citizen", "us citizens only", "clearance required"]):
        score -= 2.0
        signals.append("-US citizenship required")
    if content_lower.count("apply now") > 2:
        score -= 1.0
        signals.append("-spammy tone")

    return round(max(0, min(10, score)), 1), "; ".join(signals) if signals else "neutral quality"


def _score_location_fit(location: str, content: str) -> tuple[float, str]:
    """Score location/remote compatibility."""
    text = f"{location or ''} {content or ''}".lower()

    if any(w in text for w in ["remote", "worldwide", "anywhere", "global", "work from home"]):
        return 10.0, "remote-friendly"
    if any(w in text for w in ["india", "bangalore", "mumbai", "hyderabad", "delhi", "pune",
                                "chennai", "noida", "gurgaon"]):
        return 9.0, "India-based"
    if any(w in text for w in ["asia", "apac", "singapore", "dubai", "japan", "tokyo"]):
        return 7.0, "Asia-Pacific (relocation possible)"
    if any(w in text for w in ["hybrid", "flexible"]):
        return 6.0, "hybrid (may need relocation)"
    if any(w in text for w in ["europe", "uk", "london", "berlin", "amsterdam"]):
        return 5.0, "Europe (relocation needed)"
    if any(w in text for w in ["onsite", "on-site", "in-office"]):
        return 3.0, "onsite only"
    if any(w in text for w in ["us only", "united states", "new york", "san francisco"]):
        return 2.0, "US-based (visa needed)"

    return 5.0, "location unclear"


# ─── Main Scoring Function ──────────────────────────────────────────────────

def score_job(
    content: str,
    role: str = "",
    company: str = "",
    location: str = "",
    experience: str = "",
    domain_relevance: str = "",
    fit_score: float = None,
) -> dict:
    """Score a job across 6 dimensions and return verdict.

    Returns:
        {
            "smart_score": float (0-10),
            "verdict": "APPLY" | "CONSIDER" | "SKIP",
            "breakdown": {dimension: {"score": float, "reason": str}},
            "scored_at": str (ISO timestamp),
        }
    """
    dimensions = {
        "role_match":       _score_role_match(role, content),
        "skill_match":      _score_skill_match(content),
        "domain_relevance": _score_domain_relevance(domain_relevance, content),
        "experience_fit":   _score_experience_fit(experience, content),
        "quality_signals":  _score_quality_signals(content),
        "location_fit":     _score_location_fit(location, content),
    }

    weighted_score = sum(
        dimensions[dim][0] * WEIGHTS[dim]
        for dim in WEIGHTS
    )

    # If LLM fit_score exists, blend it in (30% LLM, 70% rule-based)
    if fit_score is not None and isinstance(fit_score, (int, float)):
        weighted_score = 0.7 * weighted_score + 0.3 * fit_score

    weighted_score = round(weighted_score, 2)

    if weighted_score >= APPLY_THRESHOLD:
        verdict = "APPLY"
    elif weighted_score >= CONSIDER_THRESHOLD:
        verdict = "CONSIDER"
    else:
        verdict = "SKIP"

    return {
        "smart_score": weighted_score,
        "verdict": verdict,
        "breakdown": {
            dim: {"score": dimensions[dim][0], "weight": WEIGHTS[dim], "reason": dimensions[dim][1]}
            for dim in WEIGHTS
        },
        "scored_at": datetime.now().isoformat(),
    }


# ─── Database Integration ───────────────────────────────────────────────────

def score_and_update(conn: sqlite3.Connection, post_id: int) -> dict:
    """Score a post and update its smart_score in the database."""
    row = conn.execute(
        """SELECT p.content, p.domain_relevance, p.fit_score, p.post_url,
                  (SELECT j.role FROM jobs j WHERE j.post_id = p.id LIMIT 1) as role,
                  (SELECT j2.company FROM jobs j2 WHERE j2.post_id = p.id LIMIT 1) as company,
                  (SELECT j3.location FROM jobs j3 WHERE j3.post_id = p.id LIMIT 1) as location,
                  (SELECT j4.experience FROM jobs j4 WHERE j4.post_id = p.id LIMIT 1) as experience
           FROM posts p WHERE p.id = ?""",
        (post_id,),
    ).fetchone()

    if not row:
        return {"error": f"Post {post_id} not found"}

    row = dict(row)
    result = score_job(
        content=row.get("content", ""),
        role=row.get("role", ""),
        company=row.get("company", ""),
        location=row.get("location", ""),
        experience=row.get("experience", ""),
        domain_relevance=row.get("domain_relevance", ""),
        fit_score=row.get("fit_score"),
    )

    # Update smart_score in DB
    try:
        conn.execute(
            "UPDATE posts SET smart_score = ? WHERE id = ?",
            (result["smart_score"], post_id),
        )
        conn.commit()
    except sqlite3.OperationalError:
        # Column might not exist yet — add it
        try:
            conn.execute("ALTER TABLE posts ADD COLUMN smart_score REAL")
            conn.execute(
                "UPDATE posts SET smart_score = ? WHERE id = ?",
                (result["smart_score"], post_id),
            )
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists, update failed for other reason

    result["post_id"] = post_id
    result["company"] = row.get("company", "")
    result["role"] = row.get("role", "")
    return result


def score_all_unscored(conn: sqlite3.Connection, limit: int = 500) -> dict:
    """Score all posts that don't have a smart_score yet."""
    # Ensure column exists
    try:
        conn.execute("ALTER TABLE posts ADD COLUMN smart_score REAL")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Already exists

    rows = conn.execute(
        """SELECT p.id FROM posts p
           WHERE p.is_hiring = 1
             AND (p.smart_score IS NULL)
           ORDER BY p.created_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()

    scored = 0
    verdicts = {"APPLY": 0, "CONSIDER": 0, "SKIP": 0}

    for row in rows:
        result = score_and_update(conn, row["id"])
        if "error" not in result:
            scored += 1
            verdicts[result["verdict"]] += 1

    return {
        "scored": scored,
        "verdicts": verdicts,
        "message": f"Scored {scored} posts: {verdicts['APPLY']} APPLY, {verdicts['CONSIDER']} CONSIDER, {verdicts['SKIP']} SKIP",
    }


def filter_unapplied(
    conn: sqlite3.Connection,
    threshold: float = APPLY_THRESHOLD,
    limit: int = 100,
) -> list[dict]:
    """Get unapplied jobs filtered by smart_score threshold.
    This replaces get_unapplied_jobs in the auto-apply pipeline.
    """
    # Ensure column exists
    try:
        conn.execute("ALTER TABLE posts ADD COLUMN smart_score REAL")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    rows = conn.execute(
        """SELECT p.id, p.post_url, p.content, p.email, p.domain_relevance,
                  p.fit_score, p.smart_score, p.source, p.apply_url,
                  (SELECT GROUP_CONCAT(j.role, ', ') FROM jobs j WHERE j.post_id = p.id) as role,
                  (SELECT j2.company FROM jobs j2 WHERE j2.post_id = p.id LIMIT 1) as company,
                  (SELECT j3.location FROM jobs j3 WHERE j3.post_id = p.id LIMIT 1) as location,
                  (SELECT j4.experience FROM jobs j4 WHERE j4.post_id = p.id LIMIT 1) as experience
           FROM posts p
           WHERE p.is_hiring = 1
             AND p.post_url NOT IN (SELECT job_url FROM applications)
             AND (p.smart_score IS NOT NULL AND p.smart_score >= ?)
           ORDER BY
             p.smart_score DESC,
             p.fit_score DESC NULLS LAST,
             CASE p.domain_relevance WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
             p.created_at DESC
           LIMIT ?""",
        (threshold, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_filter_stats(conn: sqlite3.Connection) -> dict:
    """Get statistics about smart scoring across all posts."""
    try:
        conn.execute("SELECT smart_score FROM posts LIMIT 1")
    except sqlite3.OperationalError:
        return {"error": "smart_score column not yet created — run score_all_unscored first"}

    stats = conn.execute(
        """SELECT
             COUNT(*) as total_hiring,
             COUNT(smart_score) as scored,
             COUNT(*) - COUNT(smart_score) as unscored,
             AVG(smart_score) as avg_score,
             MIN(smart_score) as min_score,
             MAX(smart_score) as max_score,
             SUM(CASE WHEN smart_score >= ? THEN 1 ELSE 0 END) as apply_count,
             SUM(CASE WHEN smart_score >= ? AND smart_score < ? THEN 1 ELSE 0 END) as consider_count,
             SUM(CASE WHEN smart_score < ? THEN 1 ELSE 0 END) as skip_count
           FROM posts
           WHERE is_hiring = 1""",
        (APPLY_THRESHOLD, CONSIDER_THRESHOLD, APPLY_THRESHOLD, CONSIDER_THRESHOLD),
    ).fetchone()

    return dict(stats) if stats else {}
