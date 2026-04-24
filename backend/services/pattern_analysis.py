"""
pattern_analysis.py — Outreach Pattern Analyzer for LinkedIn Job Parser.

Python port of career-ops/analyze-patterns.mjs, adapted for the SQLite
email-outreach schema (email_outreach, pipeline_leads, posts, jobs).

Usage:
    from db import init_db
    from pattern_analysis import analyze_patterns, get_conversion_rates

    conn = init_db()
    report = analyze_patterns(conn)
    rates  = get_conversion_rates(conn)
    conn.close()

CLI:
    python pattern_analysis.py              # JSON to stdout
    python pattern_analysis.py --summary    # human-readable table
"""

import sqlite3
import json
import sys
from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scalar(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> int:
    """Return a single integer value, defaulting to 0."""
    row = conn.execute(sql, params).fetchone()
    if row is None:
        return 0
    val = row[0] if not isinstance(row, dict) else list(row.values())[0]
    return val if val is not None else 0


def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    """Return all rows as list of dicts."""
    cur = conn.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyze_patterns(conn: sqlite3.Connection) -> dict:
    """Main analysis function.  Returns a structured dict with funnel,
    breakdowns, response-time stats, and actionable recommendations.
    Handles empty data gracefully (returns zeros, not errors).
    """

    # ── metadata ──────────────────────────────────────────────────────────
    total_sent = _scalar(conn, "SELECT COUNT(*) FROM email_outreach WHERE status = 'sent'")
    total_leads = _scalar(conn, "SELECT COUNT(*) FROM pipeline_leads")

    date_range = {"from": None, "to": None}
    row = conn.execute(
        "SELECT MIN(sent_at) AS earliest, MAX(sent_at) AS latest "
        "FROM email_outreach WHERE status = 'sent' AND sent_at IS NOT NULL"
    ).fetchone()
    if row:
        date_range["from"] = row[0] if not isinstance(row, dict) else row.get("earliest")
        date_range["to"] = row[1] if not isinstance(row, dict) else row.get("latest")

    metadata = {
        "total_emails_sent": total_sent,
        "total_leads": total_leads,
        "date_range": date_range,
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
    }

    # ── funnel ────────────────────────────────────────────────────────────
    funnel = {
        "sent": total_sent,
        "replied": _scalar(conn, "SELECT COUNT(*) FROM pipeline_leads WHERE stage = 'replied'"),
        "interviewing": _scalar(conn, "SELECT COUNT(*) FROM pipeline_leads WHERE stage = 'interviewing'"),
        "offer": _scalar(conn, "SELECT COUNT(*) FROM pipeline_leads WHERE stage = 'offer'"),
        "rejected": _scalar(conn, "SELECT COUNT(*) FROM pipeline_leads WHERE stage = 'rejected'"),
    }

    # ── by domain relevance ───────────────────────────────────────────────
    by_domain = []
    for domain in ("High", "Medium", "Low"):
        sent = _scalar(
            conn,
            """SELECT COUNT(*) FROM email_outreach eo
               JOIN posts p ON p.id = eo.post_id
               WHERE eo.status = 'sent' AND p.domain_relevance = ?""",
            (domain,),
        )
        replied = _scalar(
            conn,
            """SELECT COUNT(*) FROM pipeline_leads pl
               JOIN posts p ON p.id = pl.post_id
               WHERE pl.stage IN ('replied','interviewing','offer')
                 AND p.domain_relevance = ?""",
            (domain,),
        )
        rate = round(replied / sent, 4) if sent > 0 else 0.0
        by_domain.append({"domain": domain, "sent": sent, "replied": replied, "rate": rate})

    # ── by role ───────────────────────────────────────────────────────────
    role_rows = _rows(
        conn,
        """SELECT j.role,
                  COUNT(DISTINCT eo.id)  AS sent,
                  COUNT(DISTINCT CASE WHEN pl.stage IN ('replied','interviewing','offer')
                                       THEN pl.id END) AS replied
           FROM email_outreach eo
           JOIN jobs j ON j.post_id = eo.post_id
           LEFT JOIN pipeline_leads pl ON pl.post_id = eo.post_id
           WHERE eo.status = 'sent' AND j.role IS NOT NULL AND j.role != ''
           GROUP BY j.role
           ORDER BY sent DESC""",
    )
    by_role = []
    for r in role_rows:
        sent = r["sent"] or 0
        replied = r["replied"] or 0
        rate = round(replied / sent, 4) if sent > 0 else 0.0
        by_role.append({"role": r["role"], "sent": sent, "replied": replied, "rate": rate})

    # ── by company ────────────────────────────────────────────────────────
    company_rows = _rows(
        conn,
        """SELECT j.company,
                  COUNT(DISTINCT eo.id) AS sent,
                  COUNT(DISTINCT CASE WHEN pl.stage IN ('replied','interviewing','offer')
                                       THEN pl.id END) AS replied,
                  (SELECT pl2.stage FROM pipeline_leads pl2
                   WHERE pl2.company = j.company
                   ORDER BY pl2.updated_at DESC LIMIT 1) AS latest_stage
           FROM email_outreach eo
           JOIN jobs j ON j.post_id = eo.post_id
           LEFT JOIN pipeline_leads pl ON pl.post_id = eo.post_id
           WHERE eo.status = 'sent' AND j.company IS NOT NULL AND j.company != ''
           GROUP BY j.company
           ORDER BY sent DESC""",
    )
    by_company = []
    for r in company_rows:
        by_company.append({
            "company": r["company"],
            "sent": r["sent"] or 0,
            "replied": r["replied"] or 0,
            "stage": r["latest_stage"] or "applied",
        })

    # ── response time ─────────────────────────────────────────────────────
    time_rows = _rows(
        conn,
        """SELECT julianday(pl.updated_at) - julianday(eo.sent_at) AS days
           FROM pipeline_leads pl
           JOIN email_outreach eo ON eo.id = pl.outreach_id
           WHERE pl.stage IN ('replied','interviewing','offer')
             AND eo.sent_at IS NOT NULL
             AND pl.updated_at IS NOT NULL""",
    )
    days_list = [r["days"] for r in time_rows if r["days"] is not None and r["days"] >= 0]

    if days_list:
        response_time = {
            "avg_days": round(sum(days_list) / len(days_list), 2),
            "fastest": round(min(days_list), 2),
            "slowest": round(max(days_list), 2),
        }
    else:
        response_time = {"avg_days": None, "fastest": None, "slowest": None}

    # ── recommendations ───────────────────────────────────────────────────
    recommendations = _generate_recommendations(
        funnel, by_domain, by_role, by_company, total_sent,
    )

    return {
        "metadata": metadata,
        "funnel": funnel,
        "by_domain_relevance": by_domain,
        "by_role": by_role,
        "by_company": by_company,
        "response_time": response_time,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# Conversion rates  (per-role, per-domain)
# ---------------------------------------------------------------------------

def get_conversion_rates(conn: sqlite3.Connection) -> dict:
    """Return per-role and per-domain conversion rates.

    A 'conversion' counts any lead that progressed past 'applied'
    (i.e. replied, interviewing, or offer).
    """

    # Per-role
    role_rows = _rows(
        conn,
        """SELECT j.role,
                  COUNT(DISTINCT eo.id) AS sent,
                  COUNT(DISTINCT CASE WHEN pl.stage IN ('replied','interviewing','offer')
                                       THEN pl.id END) AS converted
           FROM email_outreach eo
           JOIN jobs j ON j.post_id = eo.post_id
           LEFT JOIN pipeline_leads pl ON pl.post_id = eo.post_id
           WHERE eo.status = 'sent' AND j.role IS NOT NULL AND j.role != ''
           GROUP BY j.role
           ORDER BY sent DESC""",
    )
    per_role = {}
    for r in role_rows:
        sent = r["sent"] or 0
        converted = r["converted"] or 0
        per_role[r["role"]] = {
            "sent": sent,
            "converted": converted,
            "rate": round(converted / sent, 4) if sent > 0 else 0.0,
        }

    # Per-domain
    per_domain = {}
    for domain in ("High", "Medium", "Low"):
        sent = _scalar(
            conn,
            """SELECT COUNT(*) FROM email_outreach eo
               JOIN posts p ON p.id = eo.post_id
               WHERE eo.status = 'sent' AND p.domain_relevance = ?""",
            (domain,),
        )
        converted = _scalar(
            conn,
            """SELECT COUNT(*) FROM pipeline_leads pl
               JOIN posts p ON p.id = pl.post_id
               WHERE pl.stage IN ('replied','interviewing','offer')
                 AND p.domain_relevance = ?""",
            (domain,),
        )
        per_domain[domain] = {
            "sent": sent,
            "converted": converted,
            "rate": round(converted / sent, 4) if sent > 0 else 0.0,
        }

    return {"per_role": per_role, "per_domain": per_domain}


# ---------------------------------------------------------------------------
# Recommendation engine
# ---------------------------------------------------------------------------

_NO_REPLY_THRESHOLD = 10  # sends without any reply triggers a warning


def _generate_recommendations(
    funnel: dict,
    by_domain: list[dict],
    by_role: list[dict],
    by_company: list[dict],
    total_sent: int,
) -> list[dict]:
    """Generate actionable recommendations from the analysis data."""
    recs: list[dict] = []

    # 1. Domain relevance insight
    domain_map = {d["domain"]: d for d in by_domain}
    high = domain_map.get("High", {})
    medium = domain_map.get("Medium", {})
    low = domain_map.get("Low", {})

    if high.get("rate", 0) > medium.get("rate", 0) and high.get("sent", 0) > 0:
        recs.append({
            "action": "Focus on High relevance leads",
            "reasoning": (
                f"High-relevance leads convert at {high['rate']:.0%} "
                f"vs Medium at {medium.get('rate', 0):.0%}. "
                f"Prioritize posts with domain_relevance='High'."
            ),
            "impact": "high",
        })

    if low.get("sent", 0) > 0 and low.get("rate", 0) == 0:
        recs.append({
            "action": "Stop emailing Low relevance leads",
            "reasoning": (
                f"{low['sent']} emails sent to Low-relevance leads with 0 replies. "
                "These are unlikely to convert."
            ),
            "impact": "medium",
        })

    # 2. Role-level insight
    if by_role:
        best = max(by_role, key=lambda r: r["rate"])
        if best["rate"] > 0 and best["sent"] >= 2:
            recs.append({
                "action": f"Double down on {best['role']} roles",
                "reasoning": (
                    f"'{best['role']}' has the highest reply rate at {best['rate']:.0%} "
                    f"({best['replied']} replies from {best['sent']} sends)."
                ),
                "impact": "high",
            })

    # 3. No replies at all
    total_replied = funnel.get("replied", 0) + funnel.get("interviewing", 0) + funnel.get("offer", 0)
    if total_sent >= _NO_REPLY_THRESHOLD and total_replied == 0:
        recs.append({
            "action": "Consider changing email template",
            "reasoning": (
                f"{total_sent} emails sent with zero replies. "
                "The subject line or body may need revision."
            ),
            "impact": "high",
        })

    # 4. Unresponsive companies
    never_replied = [
        c for c in by_company
        if c["sent"] >= 2 and c["replied"] == 0
    ]
    if never_replied:
        # Pick the worst offender (most sends, no reply)
        worst = max(never_replied, key=lambda c: c["sent"])
        others = len(never_replied) - 1
        suffix = f" (and {others} other{'s' if others != 1 else ''})" if others > 0 else ""
        recs.append({
            "action": f"Deprioritize {worst['company']}{suffix}",
            "reasoning": (
                f"{worst['sent']} emails sent to {worst['company']} with no reply. "
                "Redirect effort to more responsive targets."
            ),
            "impact": "medium",
        })

    # 5. Funnel drop-off
    if funnel.get("replied", 0) > 0 and funnel.get("interviewing", 0) == 0:
        recs.append({
            "action": "Improve reply-to-interview conversion",
            "reasoning": (
                f"{funnel['replied']} replies but 0 moved to interviewing. "
                "Follow up faster or refine your pitch after the first reply."
            ),
            "impact": "medium",
        })

    return recs


# ---------------------------------------------------------------------------
# CLI  (--summary for human-readable, default JSON)
# ---------------------------------------------------------------------------

def _print_summary(result: dict) -> None:
    m = result["metadata"]
    f = result["funnel"]

    print(f"\n{'=' * 60}")
    print(f"  Outreach Pattern Analysis  --  {m['analysis_date']}")
    print(f"  {m['total_emails_sent']} emails sent  |  {m['total_leads']} leads tracked")
    if m["date_range"]["from"]:
        print(f"  Date range: {m['date_range']['from']} -> {m['date_range']['to']}")
    print(f"{'=' * 60}\n")

    # Funnel
    print("CONVERSION FUNNEL")
    print("-" * 40)
    for stage in ("sent", "replied", "interviewing", "offer", "rejected"):
        count = f[stage]
        pct = f"({count / f['sent'] * 100:.0f}%)" if f["sent"] > 0 else ""
        print(f"  {stage:<15s} {count:>4d}  {pct}")

    # Domain
    print("\nBY DOMAIN RELEVANCE")
    print("-" * 40)
    for d in result["by_domain_relevance"]:
        print(f"  {d['domain']:<8s}  sent {d['sent']:>3d}  replied {d['replied']:>3d}  rate {d['rate']:.0%}")

    # Role
    if result["by_role"]:
        print("\nBY ROLE")
        print("-" * 40)
        for r in result["by_role"][:10]:
            print(f"  {r['role']:<25s}  sent {r['sent']:>3d}  replied {r['replied']:>3d}  rate {r['rate']:.0%}")

    # Company
    if result["by_company"]:
        print("\nBY COMPANY")
        print("-" * 40)
        for c in result["by_company"][:10]:
            print(f"  {c['company']:<25s}  sent {c['sent']:>3d}  replied {c['replied']:>3d}  stage={c['stage']}")

    # Response time
    rt = result["response_time"]
    print("\nRESPONSE TIME")
    print("-" * 40)
    if rt["avg_days"] is not None:
        print(f"  Average:  {rt['avg_days']:.1f} days")
        print(f"  Fastest:  {rt['fastest']:.1f} days")
        print(f"  Slowest:  {rt['slowest']:.1f} days")
    else:
        print("  No response data yet.")

    # Recommendations
    if result["recommendations"]:
        print(f"\nRECOMMENDATIONS")
        print("=" * 60)
        for i, r in enumerate(result["recommendations"], 1):
            tag = r["impact"].upper()
            print(f"  {i}. [{tag}] {r['action']}")
            print(f"     {r['reasoning']}")

    print()


def main():
    from db import init_db

    conn = init_db()
    result = analyze_patterns(conn)

    if "--summary" in sys.argv:
        _print_summary(result)
    else:
        print(json.dumps(result, indent=2, default=str))

    conn.close()


if __name__ == "__main__":
    main()
