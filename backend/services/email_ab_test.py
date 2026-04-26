"""
Email A/B Testing — Track which email style gets replies and auto-optimize.

Generates 2 email variants per application with different hooks/proof points,
alternates between them, and tracks reply rates by variant to find the winner.

Usage:
    from services.email_ab_test import generate_ab_variants, record_outcome, get_ab_stats

    # Generate 2 variants
    a, b = generate_ab_variants(job)

    # Pick which to send (alternates automatically)
    variant = pick_variant()

    # After getting a reply, record it
    record_outcome(conn, outreach_id, variant="A", replied=True)

    # Check stats
    stats = get_ab_stats(conn)
"""

import json
import os
import random
import sqlite3
from datetime import datetime

import requests

from config import PROFILE, RESUME_SKILLS


# ─── Variant Strategies ─────────────────────────────────────────────────────

VARIANT_STRATEGIES = {
    "A": {
        "name": "proof-first",
        "description": "Lead with quantified proof point, then connect to their need",
        "instruction": "Start the email with your STRONGEST quantified achievement that matches their need. Lead with a number/metric. Then connect it to what they're building.",
    },
    "B": {
        "name": "challenge-first",
        "description": "Lead with their specific challenge, then show you've solved it",
        "instruction": "Start by referencing a SPECIFIC challenge or problem their team faces (from the JD or company context). Then show how you've solved a similar problem before, with a concrete example.",
    },
}

# Simple alternation counter
_variant_counter = {"count": 0}


def pick_variant() -> str:
    """Alternate between A and B variants."""
    _variant_counter["count"] += 1
    return "A" if _variant_counter["count"] % 2 == 0 else "B"


# ─── DB Schema ──────────────────────────────────────────────────────────────

def _ensure_ab_columns(conn: sqlite3.Connection):
    """Add variant tracking columns to email_outreach if missing."""
    migrations = [
        "ALTER TABLE email_outreach ADD COLUMN variant TEXT",
        "ALTER TABLE email_outreach ADD COLUMN variant_strategy TEXT",
    ]
    for sql in migrations:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass  # Already exists
    conn.commit()


# ─── Generate Variants ──────────────────────────────────────────────────────

def generate_ab_variants(job: dict) -> dict:
    """Generate 2 email variants using different strategies.

    Returns {"A": {"subject": ..., "body": ...}, "B": {"subject": ..., "body": ...}}
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return {"error": "GEMINI_API_KEY not set"}

    role = job.get("role", "AI/ML role")
    company = job.get("company", "the company")
    content = (job.get("content", "") or "")[:800]

    skills_list = ", ".join(list(RESUME_SKILLS.keys())[:15])

    variants = {}
    for variant_key, strategy in VARIANT_STRATEGIES.items():
        prompt = f"""Write a cold application email for a job.

STRATEGY: {strategy['instruction']}

CANDIDATE: {PROFILE['name']}, AI Engineer, {PROFILE.get('experience_years', 2)} years.
Skills: {skills_list}
Currently: Building healthcare AI systems (fax automation for US hospitals)
Key projects: Enterprise RAG (10K+ docs), Healthcare AI pipeline (Neo4j), Biomedical ETL (50K+ records/day)

TARGET: {role} at {company}
JOB CONTEXT:
{content[:500]}

RULES:
- 120-180 words max
- NO "I'm passionate about" or "caught my eye"
- Lead with proof, not assertions
- Reference something specific about the company/role
- End with "I've attached my resume" + "Best,\\nVineet"

Return ONLY:
Subject: <subject line>

<email body>"""

        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.8, "maxOutputTokens": 400},
                },
                timeout=20,
            )
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

            # Parse subject and body
            subject = ""
            body = text
            if "Subject:" in text:
                lines = text.split("\n")
                for i, line in enumerate(lines):
                    if line.strip().startswith("Subject:"):
                        subject = line.replace("Subject:", "").strip().strip('"')
                        remaining = lines[i + 1:]
                        while remaining and not remaining[0].strip():
                            remaining.pop(0)
                        body = "\n".join(remaining).strip()
                        break

            variants[variant_key] = {
                "subject": subject,
                "body": body,
                "strategy": strategy["name"],
            }
        except Exception as e:
            variants[variant_key] = {
                "subject": f"Application: {role} at {company}",
                "body": f"Error generating variant {variant_key}: {str(e)[:100]}",
                "strategy": strategy["name"],
                "error": True,
            }

    return variants


def record_variant(conn: sqlite3.Connection, outreach_id: int, variant: str, strategy: str = ""):
    """Record which variant was sent for an outreach entry."""
    _ensure_ab_columns(conn)
    try:
        conn.execute(
            "UPDATE email_outreach SET variant = ?, variant_strategy = ? WHERE id = ?",
            (variant, strategy, outreach_id),
        )
        conn.commit()
    except Exception:
        pass


# ─── Analytics ──────────────────────────────────────────────────────────────

def get_ab_stats(conn: sqlite3.Connection) -> dict:
    """Get A/B test performance statistics."""
    _ensure_ab_columns(conn)

    try:
        rows = conn.execute("""
            SELECT
                variant,
                variant_strategy,
                COUNT(*) as total_sent,
                SUM(CASE WHEN status = 'replied' THEN 1 ELSE 0 END) as replies,
                SUM(CASE WHEN status = 'bounced' THEN 1 ELSE 0 END) as bounces
            FROM email_outreach
            WHERE variant IS NOT NULL
            GROUP BY variant, variant_strategy
        """).fetchall()

        stats = {}
        for row in rows:
            r = dict(row) if hasattr(row, 'keys') else {
                "variant": row[0], "variant_strategy": row[1],
                "total_sent": row[2], "replies": row[3], "bounces": row[4],
            }
            variant = r["variant"] or "unknown"
            total = r["total_sent"] or 0
            replies = r["replies"] or 0
            stats[variant] = {
                "strategy": r["variant_strategy"] or "",
                "sent": total,
                "replies": replies,
                "bounces": r["bounces"] or 0,
                "reply_rate": round(replies / total * 100, 1) if total > 0 else 0,
            }

        # Determine winner
        winner = None
        if len(stats) >= 2:
            a_rate = stats.get("A", {}).get("reply_rate", 0)
            b_rate = stats.get("B", {}).get("reply_rate", 0)
            min_samples = 10  # Need at least 10 sends per variant
            a_sent = stats.get("A", {}).get("sent", 0)
            b_sent = stats.get("B", {}).get("sent", 0)

            if a_sent >= min_samples and b_sent >= min_samples:
                if a_rate > b_rate * 1.2:  # 20% better to declare winner
                    winner = {"variant": "A", "reason": f"A replies at {a_rate}% vs B at {b_rate}%"}
                elif b_rate > a_rate * 1.2:
                    winner = {"variant": "B", "reason": f"B replies at {b_rate}% vs A at {a_rate}%"}
                else:
                    winner = {"variant": "tie", "reason": f"No clear winner yet (A: {a_rate}%, B: {b_rate}%)"}
            else:
                winner = {"variant": "insufficient_data",
                          "reason": f"Need {min_samples}+ sends per variant (A: {a_sent}, B: {b_sent})"}

        return {"variants": stats, "winner": winner, "total_tracked": sum(s["sent"] for s in stats.values())}

    except Exception as e:
        return {"error": str(e), "variants": {}}
