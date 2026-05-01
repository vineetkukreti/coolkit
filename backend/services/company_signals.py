"""
Company Signal Scanner — Quick vet companies before applying.

Checks company health signals using Gemini:
- Recent funding/growth (positive)
- Layoffs/hiring freeze (negative)
- Company size and stage
- Glassdoor signals

Used by smart_filter to boost/penalize scores and by auto_apply
to skip companies with red flags.

Usage:
    from services.company_signals import scan_company, scan_and_cache

    signals = scan_company("Hippocratic AI")
    # {"signal": "green", "score_modifier": 0.5, "reasons": [...]}
"""

import json
import os
import sqlite3
from datetime import datetime

import requests


# ─── Signal Cache (in-memory + DB) ──────────────────────────────────────────

_signal_cache = {}  # company_name_lower -> {signal, score_modifier, reasons, cached_at}


def _ensure_signals_table(conn: sqlite3.Connection):
    """Create company_signals table if it doesn't exist."""
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS company_signals (
                company_name    TEXT PRIMARY KEY,
                signal          TEXT NOT NULL,
                score_modifier  REAL DEFAULT 0,
                reasons         TEXT,
                raw_data        TEXT,
                scanned_at      TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"[CompanySignals] Table creation failed: {e}")


def _get_cached_signal(conn: sqlite3.Connection, company: str) -> dict | None:
    """Check cache for a company signal (memory first, then DB)."""
    key = company.lower().strip()

    # Memory cache
    if key in _signal_cache:
        cached = _signal_cache[key]
        # Expire after 7 days
        try:
            cached_at = datetime.fromisoformat(cached["cached_at"])
            if (datetime.now() - cached_at).days < 7:
                return cached
        except Exception:
            pass

    # DB cache
    try:
        _ensure_signals_table(conn)
        row = conn.execute(
            "SELECT signal, score_modifier, reasons, scanned_at FROM company_signals WHERE company_name = ?",
            (key,),
        ).fetchone()
        if row:
            result = {
                "signal": row[0] if isinstance(row, tuple) else row["signal"],
                "score_modifier": row[1] if isinstance(row, tuple) else row["score_modifier"],
                "reasons": json.loads(row[2] if isinstance(row, tuple) else row["reasons"]),
                "cached_at": row[3] if isinstance(row, tuple) else row["scanned_at"],
            }
            _signal_cache[key] = result
            return result
    except Exception as e:
        print(f"[CompanySignals] Cache read failed for {company}: {e}")

    return None


def _save_signal(conn: sqlite3.Connection, company: str, result: dict):
    """Save signal to both memory and DB cache."""
    key = company.lower().strip()
    result["cached_at"] = datetime.now().isoformat()
    _signal_cache[key] = result

    try:
        _ensure_signals_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO company_signals
               (company_name, signal, score_modifier, reasons, scanned_at)
               VALUES (?, ?, ?, ?, ?)""",
            (key, result["signal"], result["score_modifier"],
             json.dumps(result["reasons"]), result["cached_at"]),
        )
        conn.commit()
    except Exception as e:
        print(f"[CompanySignals] Cache write failed for {company}: {e}")


# ─── Signal Classification ──────────────────────────────────────────────────

def scan_company(company: str, conn: sqlite3.Connection = None) -> dict:
    """Scan a company for health signals using Gemini.

    Returns:
        {
            "signal": "green" | "yellow" | "red",
            "score_modifier": float (-2.0 to +1.0),
            "reasons": [str],
            "company": str,
        }
    """
    if not company or len(company.strip()) < 2:
        return {"signal": "yellow", "score_modifier": 0, "reasons": ["unknown company"], "company": company}

    # Check cache
    if conn:
        cached = _get_cached_signal(conn, company)
        if cached:
            cached["company"] = company
            cached["from_cache"] = True
            return cached

    # Call Gemini for quick assessment
    try:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return {"signal": "yellow", "score_modifier": 0, "reasons": ["no API key"], "company": company}

        prompt = f"""Quickly assess this company's hiring health for a job seeker. Return ONLY valid JSON.

Company: {company}

Based on your knowledge, assess:
1. Is this company actively hiring or in a hiring freeze/layoffs?
2. What's their funding/financial status?
3. Any red flags (mass layoffs, lawsuits, shutting down)?
4. Company size and stage (startup/scaleup/enterprise)?

Return EXACTLY this JSON format:
{{
    "signal": "green|yellow|red",
    "reasons": ["reason1", "reason2", "reason3"],
    "company_stage": "startup|scaleup|enterprise|unknown",
    "hiring_status": "active|slow|freeze|unknown"
}}

Rules:
- "green" = actively growing, recently funded, good reviews, actively hiring
- "yellow" = uncertain, not enough info, mixed signals
- "red" = recent layoffs, hiring freeze, financial trouble, shutting down
- If you don't know the company, return "yellow" with reason "insufficient data"
- Be honest, don't guess if you don't know"""

        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300},
            },
            timeout=15,
        )
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]

        # Parse JSON
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        data = json.loads(text.strip())

        signal = data.get("signal", "yellow")
        reasons = data.get("reasons", [])

        # Convert signal to score modifier
        modifier_map = {"green": 0.5, "yellow": 0, "red": -1.5}
        score_modifier = modifier_map.get(signal, 0)

        result = {
            "signal": signal,
            "score_modifier": score_modifier,
            "reasons": reasons[:5],
            "company": company,
        }

        # Cache result
        if conn:
            _save_signal(conn, company, result)

        return result

    except Exception as e:
        return {
            "signal": "yellow",
            "score_modifier": 0,
            "reasons": [f"scan error: {str(e)[:80]}"],
            "company": company,
        }


def scan_and_cache(conn: sqlite3.Connection, company: str) -> dict:
    """Scan company and cache in DB. Convenience wrapper."""
    return scan_company(company, conn=conn)


def get_company_modifier(conn: sqlite3.Connection, company: str) -> float:
    """Get just the score modifier for a company. Returns 0 if not cached."""
    if not company:
        return 0.0
    cached = _get_cached_signal(conn, company)
    if cached:
        return cached.get("score_modifier", 0.0)
    return 0.0
