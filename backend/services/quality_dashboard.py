"""
Application Quality Dashboard — Conversion analytics for job applications.

Tracks and computes:
- Apply method → response rate
- Smart score → interview rate
- Domain → reply rate
- Platform → conversion rate
- Time of day → response rate
- Tier → success rate

Usage:
    from services.quality_dashboard import get_dashboard_data
    data = get_dashboard_data(conn)
"""

import sqlite3
from datetime import datetime


def get_dashboard_data(conn: sqlite3.Connection) -> dict:
    """Compute comprehensive application quality metrics."""

    result = {
        "generated_at": datetime.now().isoformat(),
        "overview": _get_overview(conn),
        "by_method": _get_by_method(conn),
        "by_domain": _get_by_domain(conn),
        "by_platform": _get_by_platform(conn),
        "by_score_bucket": _get_by_score_bucket(conn),
        "by_hour": _get_by_hour(conn),
        "email_performance": _get_email_performance(conn),
        "top_companies": _get_top_companies(conn),
        "daily_trend": _get_daily_trend(conn),
    }

    return result


def _get_overview(conn: sqlite3.Connection) -> dict:
    """Overall application statistics."""
    try:
        row = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'applied' THEN 1 ELSE 0 END) as applied,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped
            FROM applications
        """).fetchone()
        r = dict(row) if hasattr(row, 'keys') else {
            "total": row[0], "applied": row[1], "failed": row[2],
            "pending": row[3], "skipped": row[4],
        }

        # Email outreach stats
        email_row = conn.execute("""
            SELECT
                COUNT(*) as total_sent,
                SUM(CASE WHEN status = 'replied' THEN 1 ELSE 0 END) as replied,
                SUM(CASE WHEN status = 'bounced' THEN 1 ELSE 0 END) as bounced
            FROM email_outreach WHERE status IN ('sent', 'replied', 'bounced')
        """).fetchone()
        er = dict(email_row) if hasattr(email_row, 'keys') else {
            "total_sent": email_row[0], "replied": email_row[1], "bounced": email_row[2],
        }

        total_sent = er.get("total_sent", 0) or 0
        replied = er.get("replied", 0) or 0

        r["emails_sent"] = total_sent
        r["emails_replied"] = replied
        r["email_reply_rate"] = round(replied / total_sent * 100, 1) if total_sent > 0 else 0
        r["success_rate"] = round(r["applied"] / r["total"] * 100, 1) if r["total"] > 0 else 0

        return r
    except Exception as e:
        return {"error": str(e)}


def _get_by_method(conn: sqlite3.Connection) -> list[dict]:
    """Conversion by apply method."""
    try:
        rows = conn.execute("""
            SELECT
                apply_method,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'applied' THEN 1 ELSE 0 END) as applied,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM applications
            WHERE apply_method IS NOT NULL
            GROUP BY apply_method
            ORDER BY total DESC
        """).fetchall()
        return [
            {
                "method": (dict(r) if hasattr(r, 'keys') else {"apply_method": r[0], "total": r[1], "applied": r[2], "failed": r[3]}).get("apply_method", r[0] if isinstance(r, tuple) else ""),
                "total": r[1] if isinstance(r, tuple) else r["total"],
                "applied": r[2] if isinstance(r, tuple) else r["applied"],
                "failed": r[3] if isinstance(r, tuple) else r["failed"],
                "success_rate": round((r[2] if isinstance(r, tuple) else r["applied"]) / (r[1] if isinstance(r, tuple) else r["total"]) * 100, 1) if (r[1] if isinstance(r, tuple) else r["total"]) > 0 else 0,
            }
            for r in rows
        ]
    except Exception:
        return []


def _get_by_domain(conn: sqlite3.Connection) -> list[dict]:
    """Conversion by domain relevance (High/Medium/Low)."""
    try:
        rows = conn.execute("""
            SELECT
                p.domain_relevance,
                COUNT(*) as total,
                SUM(CASE WHEN a.status = 'applied' THEN 1 ELSE 0 END) as applied
            FROM applications a
            JOIN posts p ON a.post_id = p.id
            WHERE p.domain_relevance IS NOT NULL
            GROUP BY p.domain_relevance
            ORDER BY total DESC
        """).fetchall()
        return [
            {
                "domain": r[0] if isinstance(r, tuple) else r["domain_relevance"],
                "total": r[1] if isinstance(r, tuple) else r["total"],
                "applied": r[2] if isinstance(r, tuple) else r["applied"],
                "success_rate": round(r[2] / r[1] * 100, 1) if (r[1] if isinstance(r, tuple) else r["total"]) > 0 else 0,
            }
            for r in rows
        ]
    except Exception:
        return []


def _get_by_platform(conn: sqlite3.Connection) -> list[dict]:
    """Conversion by platform."""
    try:
        rows = conn.execute("""
            SELECT
                platform,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'applied' THEN 1 ELSE 0 END) as applied,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM applications
            GROUP BY platform
            ORDER BY total DESC
        """).fetchall()
        return [
            {
                "platform": r[0] if isinstance(r, tuple) else r["platform"],
                "total": r[1] if isinstance(r, tuple) else r["total"],
                "applied": r[2] if isinstance(r, tuple) else r["applied"],
                "failed": r[3] if isinstance(r, tuple) else r["failed"],
                "success_rate": round(r[2] / r[1] * 100, 1) if r[1] > 0 else 0,
            }
            for r in rows
        ]
    except Exception:
        return []


def _get_by_score_bucket(conn: sqlite3.Connection) -> list[dict]:
    """Conversion by smart_score buckets."""
    try:
        # Check if smart_score column exists
        conn.execute("SELECT smart_score FROM posts LIMIT 1")
    except Exception:
        return []

    try:
        rows = conn.execute("""
            SELECT
                CASE
                    WHEN p.smart_score >= 7.0 THEN '7+ (PREMIUM)'
                    WHEN p.smart_score >= 5.0 THEN '5-7 (STANDARD)'
                    WHEN p.smart_score >= 3.5 THEN '3.5-5 (BASIC)'
                    WHEN p.smart_score IS NOT NULL THEN '<3.5 (SKIP)'
                    ELSE 'unscored'
                END as score_bucket,
                COUNT(*) as total,
                SUM(CASE WHEN a.status = 'applied' THEN 1 ELSE 0 END) as applied,
                AVG(p.smart_score) as avg_score
            FROM applications a
            JOIN posts p ON a.post_id = p.id
            GROUP BY score_bucket
            ORDER BY avg_score DESC
        """).fetchall()
        return [
            {
                "bucket": r[0] if isinstance(r, tuple) else r["score_bucket"],
                "total": r[1] if isinstance(r, tuple) else r["total"],
                "applied": r[2] if isinstance(r, tuple) else r["applied"],
                "avg_score": round(r[3], 2) if r[3] else None,
                "success_rate": round(r[2] / r[1] * 100, 1) if r[1] > 0 else 0,
            }
            for r in rows
        ]
    except Exception:
        return []


def _get_by_hour(conn: sqlite3.Connection) -> list[dict]:
    """Application success by hour of day."""
    try:
        rows = conn.execute("""
            SELECT
                CAST(strftime('%H', applied_at) AS INTEGER) as hour,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'applied' THEN 1 ELSE 0 END) as applied
            FROM applications
            WHERE applied_at IS NOT NULL
            GROUP BY hour
            ORDER BY hour
        """).fetchall()
        return [
            {
                "hour": r[0] if isinstance(r, tuple) else r["hour"],
                "total": r[1] if isinstance(r, tuple) else r["total"],
                "applied": r[2] if isinstance(r, tuple) else r["applied"],
                "success_rate": round(r[2] / r[1] * 100, 1) if r[1] > 0 else 0,
            }
            for r in rows
        ]
    except Exception:
        return []


def _get_email_performance(conn: sqlite3.Connection) -> dict:
    """Email outreach performance breakdown."""
    try:
        # By domain relevance
        rows = conn.execute("""
            SELECT
                p.domain_relevance,
                COUNT(*) as sent,
                SUM(CASE WHEN eo.status = 'replied' THEN 1 ELSE 0 END) as replied
            FROM email_outreach eo
            JOIN posts p ON eo.post_id = p.id
            WHERE eo.status IN ('sent', 'replied', 'bounced')
            GROUP BY p.domain_relevance
        """).fetchall()

        by_domain = [
            {
                "domain": r[0] if isinstance(r, tuple) else r["domain_relevance"],
                "sent": r[1] if isinstance(r, tuple) else r["sent"],
                "replied": r[2] if isinstance(r, tuple) else r["replied"],
                "reply_rate": round(r[2] / r[1] * 100, 1) if r[1] > 0 else 0,
            }
            for r in rows
        ]

        return {"by_domain": by_domain}
    except Exception:
        return {"by_domain": []}


def _get_top_companies(conn: sqlite3.Connection) -> list[dict]:
    """Top companies by application volume."""
    try:
        rows = conn.execute("""
            SELECT
                company,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'applied' THEN 1 ELSE 0 END) as applied
            FROM applications
            WHERE company IS NOT NULL AND company != ''
            GROUP BY company
            ORDER BY total DESC
            LIMIT 15
        """).fetchall()
        return [
            {
                "company": r[0] if isinstance(r, tuple) else r["company"],
                "total": r[1] if isinstance(r, tuple) else r["total"],
                "applied": r[2] if isinstance(r, tuple) else r["applied"],
            }
            for r in rows
        ]
    except Exception:
        return []


def _get_daily_trend(conn: sqlite3.Connection) -> list[dict]:
    """Daily application trend (last 30 days)."""
    try:
        rows = conn.execute("""
            SELECT
                date,
                applied,
                failed,
                skipped,
                target
            FROM daily_quotas
            ORDER BY date DESC
            LIMIT 30
        """).fetchall()
        return [
            {
                "date": r[0] if isinstance(r, tuple) else r["date"],
                "applied": r[1] if isinstance(r, tuple) else r["applied"],
                "failed": r[2] if isinstance(r, tuple) else r["failed"],
                "skipped": r[3] if isinstance(r, tuple) else r["skipped"],
                "target": r[4] if isinstance(r, tuple) else r["target"],
            }
            for r in rows
        ]
    except Exception:
        return []
