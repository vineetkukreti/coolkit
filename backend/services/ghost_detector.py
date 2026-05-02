"""Ghost Job Detector — scores job listings for freshness and legitimacy."""

import re
import sqlite3
from datetime import datetime, timedelta
from db import init_db


def compute_ghost_score(post: dict) -> dict:
    """Score a job posting 0-100 for likelihood of being a ghost/stale job.

    Higher score = MORE likely to be a real, active job.
    Lower score = MORE likely ghost/stale.

    Signals:
    1. Age (days since posted) — max 30 points
    2. Liveness (is_live check result) — max 25 points
    3. Content quality (JD length, specificity) — max 20 points
    4. Source reliability — max 15 points
    5. Repost detection (same company+role posted multiple times) — max 10 points
    """
    score = 0
    signals = []

    # 1. Age scoring (30 points max)
    created = post.get("created_at", "")
    if created:
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", ""))
            age_days = (datetime.now() - created_dt).days
            if age_days <= 3:
                score += 30
                signals.append({"signal": f"Posted {age_days}d ago — very fresh", "positive": True, "points": 30})
            elif age_days <= 7:
                score += 25
                signals.append({"signal": f"Posted {age_days}d ago — fresh", "positive": True, "points": 25})
            elif age_days <= 14:
                score += 18
                signals.append({"signal": f"Posted {age_days}d ago — recent", "positive": True, "points": 18})
            elif age_days <= 30:
                score += 10
                signals.append({"signal": f"Posted {age_days}d ago — getting stale", "positive": False, "points": 10})
            elif age_days <= 60:
                score += 5
                signals.append({"signal": f"Posted {age_days}d ago — likely stale", "positive": False, "points": 5})
            else:
                signals.append({"signal": f"Posted {age_days}d ago — probably ghost", "positive": False, "points": 0})
        except Exception:
            score += 15  # Unknown age, neutral
            signals.append({"signal": "Unknown posting date", "positive": False, "points": 15})
    else:
        score += 15
        signals.append({"signal": "No posting date available", "positive": False, "points": 15})

    # 2. Liveness (25 points)
    is_live = post.get("is_live")
    if is_live == 1:
        score += 25
        signals.append({"signal": "URL confirmed active", "positive": True, "points": 25})
    elif is_live == 0:
        signals.append({"signal": "URL expired or dead", "positive": False, "points": 0})
    elif is_live == -1:
        score += 10
        signals.append({"signal": "URL status uncertain", "positive": False, "points": 10})
    else:
        score += 12  # Not checked yet
        signals.append({"signal": "Liveness not checked yet", "positive": False, "points": 12})

    # 3. Content quality (20 points)
    content = post.get("content", "") or ""
    content_len = len(content)
    if content_len >= 500:
        score += 20
        signals.append({"signal": "Detailed job description", "positive": True, "points": 20})
    elif content_len >= 200:
        score += 15
        signals.append({"signal": "Moderate description length", "positive": True, "points": 15})
    elif content_len >= 50:
        score += 8
        signals.append({"signal": "Brief description", "positive": False, "points": 8})
    else:
        signals.append({"signal": "Very short/no description — suspicious", "positive": False, "points": 0})

    # Check for specificity signals
    specificity_keywords = ["salary", "compensation", "benefits", "equity", "team size",
                           "reporting to", "tech stack", "responsibilities", "requirements",
                           "interview process", "start date", "remote", "hybrid"]
    matches = sum(1 for kw in specificity_keywords if kw in content.lower())
    if matches >= 4:
        score += 5  # Bonus for specific JD
        signals.append({"signal": f"{matches} specificity markers found", "positive": True, "points": 5})

    # 4. Source reliability (15 points)
    source = (post.get("source") or "").lower()
    reliable_sources = {"linkedin_hiring": 15, "linkedin_feed": 12, "naukri": 13,
                       "wellfound": 14, "career_page": 15, "company_site": 15}
    less_reliable = {"generic": 8, "aggregator": 6, "unknown": 5}
    source_score = reliable_sources.get(source, less_reliable.get(source, 10))
    score += source_score
    signals.append({"signal": f"Source: {source or 'unknown'}", "positive": source_score >= 12, "points": source_score})

    # 5. Repost detection (10 points) — checked separately via DB
    repost_score = post.get("_repost_score", 10)  # Default: assume not a repost
    score += repost_score
    if repost_score < 10:
        signals.append({"signal": "Multiple similar postings from this company", "positive": False, "points": repost_score})
    else:
        signals.append({"signal": "No duplicate postings detected", "positive": True, "points": 10})

    # Clamp to 0-100
    score = max(0, min(100, score))

    # Verdict
    if score >= 75:
        verdict = "likely_active"
        label = "Likely Active"
    elif score >= 50:
        verdict = "uncertain"
        label = "Uncertain"
    elif score >= 25:
        verdict = "likely_stale"
        label = "Likely Stale"
    else:
        verdict = "ghost"
        label = "Probably Ghost"

    return {
        "ghost_score": score,
        "verdict": verdict,
        "label": label,
        "signals": signals,
    }


def check_reposts(conn: sqlite3.Connection, post_id: int, company: str, role: str) -> int:
    """Check if the same company+role has been posted multiple times. Returns score 0-10."""
    if not company or not role:
        return 10  # Can't check, assume OK

    similar = conn.execute(
        """SELECT COUNT(*) FROM jobs j
           JOIN posts p ON p.id = j.post_id
           WHERE j.company LIKE ? AND j.role LIKE ? AND j.post_id != ?""",
        (f"%{company}%", f"%{role}%", post_id)
    ).fetchone()[0]

    if similar == 0:
        return 10
    elif similar == 1:
        return 7  # One other posting — might be different team
    elif similar <= 3:
        return 4  # Multiple postings — suspicious
    else:
        return 1  # Many reposts — likely ghost/evergreen


def score_ghost_batch(conn: sqlite3.Connection, limit: int = 100) -> dict:
    """Score a batch of unscored or stale-scored posts for ghost likelihood."""
    rows = conn.execute(
        """SELECT p.id, p.post_url, p.content, p.created_at, p.is_live, p.source, p.smart_score,
                  j.role, j.company, j.location
           FROM posts p
           LEFT JOIN jobs j ON j.post_id = p.id
           WHERE p.is_hiring = 1
           ORDER BY p.created_at DESC
           LIMIT ?""",
        (limit,)
    ).fetchall()

    scored = 0
    results = []
    for row in rows:
        row = dict(row)
        # Check reposts
        repost_score = check_reposts(conn, row["id"], row.get("company", ""), row.get("role", ""))
        row["_repost_score"] = repost_score

        result = compute_ghost_score(row)
        result["post_id"] = row["id"]
        result["role"] = row.get("role", "")
        result["company"] = row.get("company", "")
        results.append(result)
        scored += 1

    # Stats
    verdicts = {}
    for r in results:
        v = r["verdict"]
        verdicts[v] = verdicts.get(v, 0) + 1

    return {
        "scored": scored,
        "verdicts": verdicts,
        "results": results,
    }


def get_ghost_stats(conn: sqlite3.Connection) -> dict:
    """Get ghost job statistics across all scored posts."""
    total = conn.execute("SELECT COUNT(*) FROM posts WHERE is_hiring = 1").fetchone()[0]

    # Age distribution
    age_buckets = {}
    for label, days in [("< 3 days", 3), ("3-7 days", 7), ("1-2 weeks", 14), ("2-4 weeks", 30), ("1-2 months", 60), ("2+ months", 9999)]:
        count = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE is_hiring = 1 AND created_at >= datetime('now', ?)",
            (f"-{days} days",)
        ).fetchone()[0]
        age_buckets[label] = count

    # Liveness stats
    live = conn.execute("SELECT COUNT(*) FROM posts WHERE is_hiring = 1 AND is_live = 1").fetchone()[0]
    dead = conn.execute("SELECT COUNT(*) FROM posts WHERE is_hiring = 1 AND is_live = 0").fetchone()[0]
    uncertain = conn.execute("SELECT COUNT(*) FROM posts WHERE is_hiring = 1 AND is_live = -1").fetchone()[0]
    unchecked = conn.execute("SELECT COUNT(*) FROM posts WHERE is_hiring = 1 AND is_live IS NULL").fetchone()[0]

    return {
        "total_hiring_posts": total,
        "liveness": {"active": live, "expired": dead, "uncertain": uncertain, "unchecked": unchecked},
        "age_buckets": age_buckets,
    }
