"""Career copilot features modeled on commercial job-search tools.

Clean-room re-implementations of publicly advertised features:
  - Cover letter generator      (Teal, Kickresume, Careerflow)
  - Salary estimator            (Levels.fyi / Glassdoor-style ranges, LLM-estimated)
  - LinkedIn profile optimizer  (Careerflow, Jobscan LinkedIn Optimization)
  - Mock interview grader       (Final Round AI, Yoodli, Huntr)
  - Weekly goals + streaks      (Huntr, Teal goal tracking)
  - One-click job save          (Teal / Simplify / Huntr browser extensions)
"""

import json
import sqlite3
from datetime import datetime, timedelta

from config import PROFILE
from services.ai_tools import CANDIDATE_PROFILE, _call_gemini, _parse_json_response


def _llm_json(prompt: str, max_tokens: int = 1500, temperature: float = 0.5) -> dict:
    text = ""
    try:
        text = _call_gemini(prompt, max_tokens=max_tokens, temperature=temperature)
        return _parse_json_response(text)
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        return {"error": f"Failed to parse LLM response: {exc}", "raw": text}
    except Exception as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 1. Cover letter (Teal / Kickresume)
# ---------------------------------------------------------------------------

COVER_LETTER_TONES = ("professional", "enthusiastic", "concise", "storytelling")


def generate_cover_letter(jd_text: str, company: str = "", role: str = "", tone: str = "professional") -> dict:
    tone = tone if tone in COVER_LETTER_TONES else "professional"
    prompt = f"""You write cover letters that get interviews. Write one for this candidate.

━━━ CANDIDATE ━━━
{CANDIDATE_PROFILE}

━━━ TARGET ━━━
Company: {company or "(infer from JD)"}
Role: {role or "(infer from JD)"}
Tone: {tone}

━━━ JOB DESCRIPTION ━━━
{jd_text[:6000]}

━━━ RULES ━━━
- 250-350 words, 3-4 paragraphs. No "I am writing to apply" openers.
- Open with a specific hook tied to the company's product or mission.
- Map 2-3 of the candidate's REAL projects/achievements to the JD's top requirements. Never invent experience.
- Close with a concrete call to action.

Return ONLY JSON:
{{
  "subject": "<email subject line if sent by email>",
  "cover_letter": "<full letter text with \\n\\n between paragraphs>",
  "requirements_matched": ["<JD requirement -> candidate evidence>", "..."],
  "gaps_not_addressed": ["<JD requirement the candidate lacks>"]
}}"""
    return _llm_json(prompt, max_tokens=1500, temperature=0.6)


# ---------------------------------------------------------------------------
# 2. Salary estimate (Levels.fyi / Glassdoor style)
# ---------------------------------------------------------------------------

def estimate_salary(role: str, company: str = "", location: str = "", experience_years: float | None = None) -> dict:
    if experience_years is None:
        experience_years = PROFILE.get("experience_years", 0)
    location = location or PROFILE.get("location", "")
    prompt = f"""You are a compensation analyst. Estimate the market pay for this role.
Role: {role}
Company: {company or "(unknown / typical market)"}
Location: {location or "(unspecified)"}
Candidate experience: {experience_years} years

Return ONLY JSON:
{{
  "currency": "<ISO code appropriate to location, e.g. INR, USD>",
  "period": "annual",
  "base": {{"p25": <number>, "p50": <number>, "p75": <number>}},
  "total_comp": {{"p25": <number>, "p50": <number>, "p75": <number>}},
  "level_guess": "<likely level/title band at this company>",
  "factors": ["<what moves pay up or down for this role>"],
  "negotiation_tips": ["<3-5 specific tips>"],
  "suggested_ask": <number, total comp to ask for>,
  "confidence": "<low|medium|high>"
}}
These are model estimates, not live data; set confidence honestly."""
    result = _llm_json(prompt, max_tokens=900, temperature=0.3)
    if "error" not in result:
        result["disclaimer"] = "LLM estimate — verify against Levels.fyi, Glassdoor or AmbitionBox before negotiating."
    return result


# ---------------------------------------------------------------------------
# 3. LinkedIn profile optimizer (Careerflow / Jobscan)
# ---------------------------------------------------------------------------

def optimize_linkedin(headline: str = "", about: str = "", target_role: str = "") -> dict:
    prompt = f"""You are a LinkedIn profile optimization expert (recruiter-search SEO).

━━━ CANDIDATE ━━━
{CANDIDATE_PROFILE}

Target role: {target_role or PROFILE.get("current_title", "")}
Current headline: {headline or "(not provided)"}
Current About section: {about or "(not provided)"}

Return ONLY JSON:
{{
  "score": <0-100 current profile strength>,
  "headline_options": ["<3 headlines, max 220 chars, keyword-dense but human>"],
  "about": "<rewritten About section, 150-250 words, first 2 lines are a hook>",
  "missing_keywords": ["<recruiter search keywords absent from the profile>"],
  "featured_suggestions": ["<what to pin in Featured>"],
  "quick_wins": ["<5 concrete edits ranked by impact>"]
}}
Use only the candidate's real experience."""
    return _llm_json(prompt, max_tokens=1500, temperature=0.6)


# ---------------------------------------------------------------------------
# 4. Mock interview (Final Round AI / Yoodli)
# ---------------------------------------------------------------------------

def mock_interview_question(company: str, role: str, round_type: str = "behavioral", asked: list | None = None) -> dict:
    prompt = f"""You are interviewing a candidate for {role} at {company}. Round: {round_type}.
Already asked (do not repeat): {json.dumps(asked or [])}
Candidate background: {CANDIDATE_PROFILE[:1500]}

Return ONLY JSON: {{"question": "<one realistic interview question>", "what_good_looks_like": "<1-2 sentences>"}}"""
    return _llm_json(prompt, max_tokens=300, temperature=0.8)


def grade_interview_answer(question: str, answer: str, role: str = "") -> dict:
    prompt = f"""You are a strict but supportive interview coach. Grade this answer.
Role: {role}
Question: {question}
Answer: {answer[:4000]}

Return ONLY JSON:
{{
  "score": <1-10>,
  "structure": "<STAR / clarity assessment>",
  "strengths": ["..."],
  "improvements": ["<specific, actionable>"],
  "filler_or_vague_phrases": ["<quotes from the answer>"],
  "model_answer": "<a stronger version in the candidate's voice, under 200 words>",
  "follow_up_question": "<what an interviewer would probe next>"
}}"""
    return _llm_json(prompt, max_tokens=1200, temperature=0.4)


# ---------------------------------------------------------------------------
# 5. Weekly goals + streaks (Huntr / Teal)
# ---------------------------------------------------------------------------

DEFAULT_GOALS = {"applications": 15, "outreach": 20, "followups": 10}


def _ensure_goals_table(conn: sqlite3.Connection):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS weekly_goals (
               metric TEXT PRIMARY KEY,
               target INTEGER NOT NULL
           )"""
    )


def set_goals(conn: sqlite3.Connection, goals: dict) -> dict:
    _ensure_goals_table(conn)
    for metric, target in goals.items():
        if metric in DEFAULT_GOALS:
            conn.execute(
                "INSERT INTO weekly_goals (metric, target) VALUES (?, ?) "
                "ON CONFLICT(metric) DO UPDATE SET target = excluded.target",
                (metric, max(0, int(target))),
            )
    conn.commit()
    return get_goal_progress(conn)


def _count_since(conn, sql: str, since: str) -> int:
    try:
        return conn.execute(sql, (since,)).fetchone()[0] or 0
    except sqlite3.OperationalError:
        return 0


def _active_days(conn) -> set:
    days = set()
    for sql in (
        "SELECT DISTINCT date(applied_at, 'localtime') FROM applications WHERE status = 'applied'",
        "SELECT DISTINCT date(sent_at, 'localtime') FROM email_outreach WHERE sent_at IS NOT NULL",
    ):
        try:
            days.update(r[0] for r in conn.execute(sql).fetchall() if r[0])
        except sqlite3.OperationalError:
            pass
    return days


def get_goal_progress(conn: sqlite3.Connection) -> dict:
    _ensure_goals_table(conn)
    targets = dict(DEFAULT_GOALS)
    targets.update({r[0]: r[1] for r in conn.execute("SELECT metric, target FROM weekly_goals").fetchall()})

    today = datetime.now().date()
    week_start = (today - timedelta(days=today.weekday())).isoformat()
    done = {
        "applications": _count_since(conn, "SELECT COUNT(*) FROM applications WHERE status = 'applied' AND date(applied_at, 'localtime') >= ?", week_start),
        "outreach": _count_since(conn, "SELECT COUNT(*) FROM email_outreach WHERE sent_at IS NOT NULL AND date(sent_at, 'localtime') >= ?", week_start),
        "followups": _count_since(conn, "SELECT COUNT(*) FROM email_outreach WHERE followup_count > 0 AND date(sent_at, 'localtime') >= ?", week_start),
    }

    days = _active_days(conn)
    streak, cursor = 0, today
    if cursor.isoformat() not in days:  # today not done yet doesn't break the streak
        cursor -= timedelta(days=1)
    while cursor.isoformat() in days:
        streak += 1
        cursor -= timedelta(days=1)

    return {
        "status": "ok",
        "week_start": week_start,
        "goals": [
            {"metric": m, "target": targets[m], "done": done[m],
             "pct": min(100, round(100 * done[m] / targets[m])) if targets[m] else 100}
            for m in DEFAULT_GOALS
        ],
        "streak_days": streak,
        "active_today": today.isoformat() in days,
    }


# ---------------------------------------------------------------------------
# 6. One-click save from browser extension (Teal / Simplify / Huntr)
# ---------------------------------------------------------------------------

def save_job_from_page(conn: sqlite3.Connection, url: str, title: str = "", company: str = "",
                       location: str = "", page_text: str = "", status: str = "pending") -> dict:
    from db import log_application
    from services.ats_scorer import compute_ats_score

    platform = "extension"
    for host in ("linkedin", "naukri", "greenhouse", "lever", "workday", "ashby", "indeed", "wellfound"):
        if host in url:
            platform = host
            break

    app_id = log_application(conn, platform=platform, job_url=url, job_title=title, company=company,
                             location=location, status=status if status in ("pending", "applied") else "pending",
                             apply_method="extension")
    ats = compute_ats_score(page_text) if page_text.strip() else None
    return {
        "status": "ok" if app_id else "duplicate",
        "message": "Saved to tracker" if app_id else "Already in tracker",
        "application_id": app_id,
        "ats": ats,
    }


# ---------------------------------------------------------------------------
# 7. Reply drafts for job emails (interview invites, offers, recruiter pings)
# ---------------------------------------------------------------------------

def draft_email_reply(subject: str, body: str, email_type: str, from_addr: str = "") -> dict:
    goal = {
        "interview": "accept the interview and propose 2-3 time windows as [placeholders] for the candidate to fill in",
        "offer": "thank them warmly, confirm interest, and ask for the written offer / next steps without committing",
        "rejection": "thank them briefly and ask to be considered for future roles",
        "confirmation": "no reply usually needed; write a one-line polite acknowledgement",
    }.get(email_type, "reply helpfully and briefly")
    prompt = f"""Draft a reply from this candidate to a job-related email. Goal: {goal}.

Candidate: {PROFILE.get("name", "")}, {PROFILE.get("current_title", "")}
From: {from_addr}
Subject: {subject}
Email:
{body[:2500]}

Rules: under 120 words, warm and direct, no clichés, never invent dates or facts — use [placeholders].
Return ONLY JSON: {{"subject": "Re: ...", "body": "<reply text>"}}"""
    return _llm_json(prompt, max_tokens=500, temperature=0.4)
