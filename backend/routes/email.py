"""Email outreach routes — generate, send, bulk operations, and history."""

import random
import threading
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import init_db
from services.email_service import (
    email_worker_state,
    generate_worker_state,
    send_worker_state,
    _email_lock,
    _generate_lock,
    _send_lock,
    generate_email,
    send_email,
    is_email_blocked,
    verify_email,
    _bulk_generate_worker,
    _bulk_send_worker,
    validate_email_before_send,
    get_bounce_blocked_domains,
    SMTP_CONFIG,
)

router = APIRouter()

_local = threading.local()


def _get_db():
    # Honor an explicitly-set connection (used directly by tests).
    override = getattr(_local, 'conn', None)
    if override is not None:
        return override
    # Otherwise keep one connection per user PER THREAD. Thread-local keeps each
    # connection confined to one thread (SQLite-safe); keying by user id stops a
    # pooled thread from serving user B with the connection it opened for user A.
    from db import current_user_id
    uid = current_user_id.get()
    cache = getattr(_local, 'by_user', None)
    if cache is None:
        cache = _local.by_user = {}
    conn = cache.get(uid)
    if conn is None:
        conn = cache[uid] = init_db()
    return conn


# ───────────────────────────────────────────────
# Pydantic models
# ───────────────────────────────────────────────

class EmailGenerateRequest(BaseModel):
    post_id: int = 0
    author_name: str = ""
    author_headline: str = ""
    role: str = ""
    company: str = ""
    location: str = ""
    domain_relevance: str = ""
    is_hiring: bool = True
    content: str = ""
    to_email: str = ""


class EmailSendRequest(BaseModel):
    post_id: int = 0
    to_email: str
    subject: str
    body: str
    attach_resume: bool = True
    source: str = "scraped"
    phone: str = ""
    hashtags: str = ""
    work_mode: str = ""
    company: str = ""
    role: str = ""
    location: str = ""
    experience: str = ""


class BulkEmailRequest(BaseModel):
    post_ids: list[int]


class SaveDraftRequest(BaseModel):
    post_id: int
    to_email: str
    subject: str
    body: str
    source: str = "scraped"
    phone: str = ""
    hashtags: str = ""
    work_mode: str = ""
    company: str = ""
    role: str = ""
    location: str = ""
    experience: str = ""
    posted_at: str = ""
    skills_json: str = ""


class BulkSendRequest(BaseModel):
    attach_resume: bool = True


class EmailVerifyRequest(BaseModel):
    email: str
    company: str = ""


class PasteExtractRequest(BaseModel):
    raw_text: str
    posted_times: list[str] = []  # Optional: relative timestamps per post, e.g. ["3d", "1w", "2mo"]


# ───────────────────────────────────────────────
# Routes
# ───────────────────────────────────────────────

@router.post("/api/email/verify")
def api_verify_email(req: EmailVerifyRequest):
    """Test if an email address is deliverable before sending.

    Runs full verification: sanitize → blocklist → generic → format → MX → SMTP RCPT TO.
    Use this to check any email before committing to a send.
    """
    result = verify_email(req.email, req.company)
    return {
        "status": "ok",
        "original": req.email,
        "sanitized": result["email"],
        "valid": result["valid"],
        "reason": result["reason"],
        "smtp_status": result["smtp_status"],
    }


@router.post("/api/email/paste-extract")
def api_paste_extract(req: PasteExtractRequest):
    """Extract structured data from pasted LinkedIn hiring post text.

    Splits on 3+ blank lines or --- dividers, then runs the full extraction pipeline
    (regex emails, LLM extraction, domain scoring) on each chunk.
    """
    import re
    from extractors.pipeline import process_single_post
    from extractors.fitness import is_good_fit, experience_to_years
    from extractors.text import parse_relative_time

    raw_text = req.raw_text.strip()
    if not raw_text:
        return {"posts": [], "total": 0}

    # ── Smart splitting ──
    # Try 3+ blank lines first (explicit separator)
    chunks = re.split(r'\n\s*\n\s*\n|\n\s*---+\s*\n|\n\s*===+\s*\n', raw_text)
    # If only 1 chunk, try splitting on emoji-starting lines (LinkedIn posts often start with emoji)
    if len(chunks) <= 1:
        lines = raw_text.split('\n')
        emoji_pattern = re.compile(r'^[\U0001F300-\U0001FAD6\u2600-\u27BF\u2B50]')
        current, result_chunks = [], []
        for line in lines:
            if emoji_pattern.match(line.strip()) and current and len('\n'.join(current)) >= 50:
                result_chunks.append('\n'.join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            result_chunks.append('\n'.join(current))
        chunks = result_chunks if len(result_chunks) > 1 else [raw_text]

    # ── Process each chunk ──
    posts = []
    for i, chunk in enumerate(chunks):
        chunk = chunk.strip()
        if len(chunk) < 30:
            continue

        # Strip LinkedIn profile headers: "View X's profile\nX\n\n • Following\n\nTitle\n\n3mo •"
        chunk = re.sub(r'^View\s+.*?profile\s*\n.*?\n\s*•\s*(?:Following|Follow|1st|2nd|3rd\+?)\s*\n.*?\n\d+\w*\s*•\s*(?:Edited\s*•\s*)?\n*', '', chunk, flags=re.DOTALL)
        # Also strip "Join" lines and group headers
        chunk = re.sub(r'^.*?(?:HR Circle|Community).*?\n', '', chunk)
        chunk = re.sub(r'^\s*(?:Join|Following|Follow)\s*$', '', chunk, flags=re.MULTILINE)
        chunk = chunk.strip()
        if len(chunk) < 30:
            continue

        # Extract emails BEFORE truncation (emails are often at the end of long posts)
        from extractors.text import extract_emails as _extract_emails_fn, extract_phones as _extract_phones_fn
        pre_emails = _extract_emails_fn(chunk)
        pre_phones = _extract_phones_fn(chunk)

        # Truncate for LLM processing (LLM uses 500-1500 chars internally)
        chunk_for_llm = chunk[:3000]

        # Use existing extraction pipeline — skip fitness so ALL posts come through
        result = process_single_post(
            {"content": chunk_for_llm},
            dedup=None,
            conn=None,
            skip_fitness=True,
        )
        if result:
            # Merge pre-extracted emails/phones (caught before truncation)
            if pre_emails and not result.get("email"):
                result["email"] = pre_emails
            elif pre_emails and result.get("email"):
                # Merge unique emails
                existing = set(e.strip().lower() for e in result["email"].split(","))
                for e in pre_emails.split(","):
                    if e.strip().lower() not in existing:
                        result["email"] += ", " + e.strip()
            if pre_phones and not result.get("phone"):
                result["phone"] = pre_phones

            result["index"] = i
            role = result.pop("role_hiring_for", "")
            result["role"] = role
            # Fitness check: >3yr min experience → bank, location must be India/Remote
            fit, fit_reason = is_good_fit(role, result.get("experience", ""))
            if fit:
                min_yr, _ = experience_to_years(result.get("experience", ""))
                if min_yr is not None and min_yr > 3:
                    fit = False
                    fit_reason = f"exp-too-high:{min_yr}yr+"
            # Location filter: only India cities + Remote are eligible
            if fit:
                loc = (result.get("location") or "").lower()
                india_locations = ["india", "remote", "bangalore", "bengaluru", "mumbai", "delhi",
                    "hyderabad", "pune", "chennai", "kolkata", "noida", "gurgaon", "gurugram",
                    "ahmedabad", "surat", "trivandrum", "kochi", "gandhinagar", "pan india",
                    "work from home", "wfh", "hybrid"]
                if loc and not any(city in loc for city in india_locations):
                    fit = False
                    fit_reason = f"location:{result.get('location', 'unknown')}"
            result["fit"] = fit
            result["fit_reason"] = fit_reason
            # Parse relative timestamp — from explicit posted_times OR auto-detect from text
            posted_ago = ""
            if i < len(req.posted_times) and req.posted_times[i]:
                posted_ago = req.posted_times[i].strip()
            else:
                # Auto-detect: look for "3d", "1w", "2mo" etc. at the very start of the chunk
                time_match = re.match(r'^\s*(\d+\s*(?:mo|months?|w|weeks?|d|days?|h|hours?|min|minutes?|m|yr?s?))\s*[\n,]', chunk)
                if time_match:
                    posted_ago = time_match.group(1).strip()
            result["posted_at"] = parse_relative_time(posted_ago) if posted_ago else ""
            result["posted_ago"] = posted_ago
            posts.append(result)

    # Mark posts where we've already contacted that email
    if posts:
        all_emails = [p["email"].lower().strip() for p in posts if p.get("email")]
        if all_emails:
            db_conn = _get_db()
            placeholders = ",".join("?" * len(all_emails))
            sent_rows = db_conn.execute(
                f"SELECT DISTINCT LOWER(TRIM(recipient_email)) FROM email_outreach WHERE status IN ('sent', 'replied') AND LOWER(TRIM(recipient_email)) IN ({placeholders})",
                all_emails,
            ).fetchall()
            sent_set = {r[0] for r in sent_rows}
            for post in posts:
                email = (post.get("email") or "").lower().strip()
                post["already_contacted"] = email in sent_set
        else:
            for post in posts:
                post["already_contacted"] = False

    return {"posts": posts, "total": len(posts)}


@router.get("/api/email/paste-history")
def api_paste_history():
    """Get all pasted outreach contacts with full details + stats."""
    db_conn = _get_db()
    rows = db_conn.execute(
        """SELECT id, recipient_email, subject, body, status, sent_at, created_at,
                  source, phone, hashtags, work_mode, company, role, location, experience, posted_at,
                  outreach_type, error_message, error_type
           FROM email_outreach
           WHERE source = 'pasted'
           ORDER BY created_at DESC
           LIMIT 500"""
    ).fetchall()
    contacts = [dict(r) for r in rows]

    # Flag already-contacted emails (sent via any source, not just pasted)
    all_emails = [c["recipient_email"].lower().strip() for c in contacts if c.get("recipient_email")]
    sent_set = set()
    if all_emails:
        placeholders = ",".join("?" * len(all_emails))
        sent_rows = db_conn.execute(
            f"SELECT DISTINCT LOWER(TRIM(recipient_email)) FROM email_outreach WHERE status IN ('sent', 'replied') AND LOWER(TRIM(recipient_email)) IN ({placeholders})",
            all_emails,
        ).fetchall()
        sent_set = {r[0] for r in sent_rows}
    for c in contacts:
        c["already_contacted"] = (c.get("recipient_email") or "").lower().strip() in sent_set

    # Stats
    total = len(contacts)
    sent = sum(1 for c in contacts if c["status"] == "sent")
    drafted = sum(1 for c in contacts if c["status"] == "draft")
    failed = sum(1 for c in contacts if c["status"] == "failed")
    already = sum(1 for c in contacts if c.get("already_contacted"))
    with_phone = sum(1 for c in contacts if c.get("phone"))
    with_email = sum(1 for c in contacts if c.get("recipient_email"))
    unique_companies = len(set(c.get("company", "") for c in contacts if c.get("company")))

    return {
        "contacts": contacts,
        "stats": {
            "total": total,
            "sent": sent,
            "drafted": drafted,
            "failed": failed,
            "already_contacted": already,
            "with_phone": with_phone,
            "with_email": with_email,
            "unique_companies": unique_companies,
        },
    }


@router.get("/api/email/skill-demand")
def api_skill_demand():
    """Aggregate skill demand across all pasted contacts. Shows what's hot in the market."""
    import json
    db_conn = _get_db()
    rows = db_conn.execute(
        "SELECT skills_json, role FROM email_outreach WHERE source='pasted' AND skills_json IS NOT NULL AND skills_json != ''"
    ).fetchall()

    # Count each skill across all posts
    category_counts = {}  # category -> { skill: count }
    total_posts = len(rows)
    for row in rows:
        try:
            skills = json.loads(row["skills_json"])
            for cat, skill_list in skills.items():
                if cat not in category_counts:
                    category_counts[cat] = {}
                for skill in skill_list:
                    category_counts[cat][skill] = category_counts[cat].get(skill, 0) + 1
        except (json.JSONDecodeError, TypeError):
            continue

    # Sort each category by count descending
    demand = {}
    for cat, skills in category_counts.items():
        sorted_skills = sorted(skills.items(), key=lambda x: -x[1])
        demand[cat] = [{"skill": s, "count": c, "pct": round(c / total_posts * 100)} for s, c in sorted_skills]

    return {"demand": demand, "total_posts": total_posts}


@router.post("/api/email/backfill-skills")
def api_backfill_skills():
    """Backfill skills_json, phone, hashtags for all contacts. Re-extracts from available text."""
    import json
    from extractors.text import extract_skills, extract_phones, extract_hashtags
    db_conn = _get_db()

    # 1. Backfill pasted contacts from email_outreach
    rows = db_conn.execute(
        """SELECT id, body, subject, role, recipient_email, phone, hashtags, skills_json, company, location, experience
           FROM email_outreach WHERE source='pasted'"""
    ).fetchall()
    updated = 0
    for row in rows:
        content = " ".join(filter(None, [row["body"], row["subject"], row["role"], row["company"], row["location"]]))
        if len(content.strip()) < 10:
            continue

        updates = {}

        # Backfill skills
        if not row["skills_json"]:
            skills = extract_skills(content)
            if skills:
                updates["skills_json"] = json.dumps(skills)

        # Backfill phone from body text
        if not row["phone"]:
            phones = extract_phones(content)
            if phones:
                updates["phone"] = phones

        # Backfill hashtags from body text
        if not row["hashtags"]:
            tags = extract_hashtags(content)
            if tags:
                updates["hashtags"] = tags

        if updates:
            set_clause = ", ".join(f"{k}=?" for k in updates)
            db_conn.execute(f"UPDATE email_outreach SET {set_clause} WHERE id=?", (*updates.values(), row["id"]))
            updated += 1

    db_conn.commit()

    # 2. Backfill from posts table (scraped jobs) → update linked email_outreach entries
    post_rows = db_conn.execute(
        """SELECT p.id, p.content, j.role, j.company FROM posts p
           LEFT JOIN jobs j ON j.post_id = p.id
           WHERE p.content IS NOT NULL AND p.content != ''"""
    ).fetchall()
    posts_updated = 0
    for row in post_rows:
        content = (row["content"] or "") + " " + (row["role"] or "") + " " + (row["company"] or "")
        skills = extract_skills(content)
        if skills:
            result = db_conn.execute(
                "UPDATE email_outreach SET skills_json=? WHERE post_id=? AND (skills_json IS NULL OR skills_json = '')",
                (json.dumps(skills), row["id"])
            )
            if result.rowcount > 0:
                posts_updated += 1
    db_conn.commit()

    return {"status": "ok", "pasted_updated": updated, "posts_updated": posts_updated}


@router.post("/api/email/save-draft")
def api_save_draft(req: SaveDraftRequest):
    """Save or update a draft email for a post."""
    db_conn = _get_db()
    # When post_id is 0 (pasted posts), dedup on recipient_email instead
    if req.post_id:
        existing = db_conn.execute(
            "SELECT id FROM email_outreach WHERE post_id = ? AND status = 'draft'",
            (req.post_id,),
        ).fetchone()
    else:
        existing = db_conn.execute(
            "SELECT id FROM email_outreach WHERE recipient_email = ? AND status = 'draft' AND post_id IS NULL",
            (req.to_email,),
        ).fetchone()
    if existing:
        db_conn.execute(
            """UPDATE email_outreach SET recipient_email=?, subject=?, body=?,
               phone=?, hashtags=?, source=?, work_mode=?, company=?, role=?, location=?, experience=?, posted_at=?, skills_json=?,
               created_at=datetime('now') WHERE id=?""",
            (req.to_email, req.subject, req.body, req.phone or None, req.hashtags or None, req.source,
             req.work_mode or None, req.company or None, req.role or None, req.location or None, req.experience or None,
             req.posted_at or None, req.skills_json or None, existing["id"]),
        )
    else:
        pid = req.post_id if req.post_id else None
        db_conn.execute(
            """INSERT INTO email_outreach (post_id, recipient_email, subject, body, status, source, phone, hashtags,
               work_mode, company, role, location, experience, posted_at, skills_json)
               VALUES (?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (pid, req.to_email, req.subject, req.body, req.source, req.phone or None, req.hashtags or None,
             req.work_mode or None, req.company or None, req.role or None, req.location or None, req.experience or None,
             req.posted_at or None, req.skills_json or None),
        )
    db_conn.commit()
    return {"status": "ok", "message": "Draft saved"}


@router.post("/api/email/generate")
def api_generate_email(req: EmailGenerateRequest):
    """Generate personalized cold email using AI. If post_id given, fetch data from DB."""
    db_conn = _get_db()
    post_data = {}

    # If post_id provided, fetch from DB
    if req.post_id:
        row = db_conn.execute(
            """SELECT p.id, p.author_name, p.author_headline, p.content, p.email,
                      p.links, p.domain_relevance, p.is_hiring, p.post_url,
                      j.role, j.company, j.location, j.experience
               FROM posts p LEFT JOIN jobs j ON j.post_id = p.id
               WHERE p.id = ?""",
            (req.post_id,),
        ).fetchone()
        if row:
            post_data = dict(row)

    # Override with any explicitly provided fields
    if req.author_name: post_data["author_name"] = req.author_name
    if req.author_headline: post_data["author_headline"] = req.author_headline
    if req.role: post_data["role"] = req.role
    if req.company: post_data["company"] = req.company
    if req.location: post_data["location"] = req.location
    if req.domain_relevance: post_data["domain_relevance"] = req.domain_relevance
    if req.content: post_data["content"] = req.content
    post_data["is_hiring"] = req.is_hiring

    try:
        result = generate_email(post_data)
        return {"status": "ok", "post_id": req.post_id, **result}
    except Exception as e:
        print(f"Error in /api/email/generate: {e}")
        raise HTTPException(status_code=500, detail="Email generation failed. Please try again.")


@router.post("/api/email/send")
def api_send_email(req: EmailSendRequest):
    db_conn = _get_db()
    # Full pre-send verification: sanitize → blocklist → generic → format → MX → SMTP RCPT TO
    company = ""
    if req.post_id:
        row = db_conn.execute("SELECT company FROM jobs WHERE post_id = ? LIMIT 1", (req.post_id,)).fetchone()
        if row:
            company = row["company"] or ""
    check = verify_email(req.to_email, company)
    if not check["valid"]:
        raise HTTPException(status_code=400, detail=check["reason"])
    # Use sanitized email from verification
    to_email = check["email"]
    pid = req.post_id if req.post_id else None  # NULL for FK safety when no real post
    try:
        result = send_email(to_email, req.subject, req.body, attach_resume=req.attach_resume)
        if result["status"] == "sent":
            db_conn.execute(
                """INSERT INTO email_outreach (post_id, recipient_email, subject, body, status, sent_at, source, phone, hashtags,
                   work_mode, company, role, location, experience)
                   VALUES (?, ?, ?, ?, 'sent', datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?)""",
                (pid, to_email, req.subject, req.body, req.source, req.phone or None, req.hashtags or None,
                 req.work_mode or None, req.company or None, req.role or None, req.location or None, req.experience or None),
            )
            db_conn.commit()
            return {"status": "sent", "message": f"Email sent to {to_email}"}
        else:
            db_conn.execute(
                """INSERT INTO email_outreach (post_id, recipient_email, subject, body, status, error_message, error_type, source, phone, hashtags,
                   work_mode, company, role, location, experience)
                   VALUES (?, ?, ?, ?, 'failed', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (pid, to_email, req.subject, req.body, result.get("error_message", "")[:500], result.get("error_type", "unknown"),
                 req.source, req.phone or None, req.hashtags or None,
                 req.work_mode or None, req.company or None, req.role or None, req.location or None, req.experience or None),
            )
            db_conn.commit()
            raise HTTPException(status_code=500, detail=result.get("error_message", "Send failed"))
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /api/email/send: {e}")
        try:
            db_conn.execute(
                """INSERT INTO email_outreach (post_id, recipient_email, subject, body, status, error_message, error_type, source, phone, hashtags,
                   work_mode, company, role, location, experience)
                   VALUES (?, ?, ?, ?, 'failed', ?, 'unknown', ?, ?, ?, ?, ?, ?, ?, ?)""",
                (pid, to_email, req.subject, req.body, str(e)[:500], req.source, req.phone or None, req.hashtags or None,
                 req.work_mode or None, req.company or None, req.role or None, req.location or None, req.experience or None),
            )
            db_conn.commit()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Email sending failed. Please try again.")


@router.post("/api/email/bulk-generate")
def api_bulk_generate(req: BulkEmailRequest):
    """Start bulk email generation in background. Non-blocking."""
    with _generate_lock:
        if generate_worker_state["running"]:
            raise HTTPException(status_code=400, detail="Email generation already running. Wait or stop it first.")
        generate_worker_state["running"] = True

    db_conn = _get_db()
    # If no post_ids given, auto-select all outreach-ready posts + startup leads without drafts
    post_ids = req.post_ids
    if not post_ids:
        from config import PROFILE as _PROFILE
        _employer_domain = _PROFILE.get("employer_domain", "")
        rows = db_conn.execute(
            """SELECT p.id FROM posts p
               WHERE p.email IS NOT NULL AND p.email != ''
                 AND p.is_hiring = 1
                 AND (? = '' OR LOWER(p.email) NOT LIKE '%' || LOWER(?) || '%')
                 AND p.id NOT IN (SELECT post_id FROM email_outreach WHERE post_id IS NOT NULL AND status IN ('sent', 'draft'))
                 AND NOT EXISTS (
                     SELECT 1 FROM email_outreach eo
                     WHERE eo.status = 'sent'
                       AND INSTR(p.email, eo.recipient_email) > 0
                 )
               ORDER BY CASE p.domain_relevance WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END
            """,
            (_employer_domain, _employer_domain),
        ).fetchall()
        post_ids = [r["id"] for r in rows]

        # Also include startup leads with emails that haven't been contacted
        sent_emails = {r[0].lower() for r in db_conn.execute(
            "SELECT DISTINCT recipient_email FROM email_outreach WHERE status IN ('sent', 'replied', 'draft')"
        ).fetchall()}
        lead_rows = db_conn.execute(
            """SELECT id, company_name, email, description, industry, location,
                      website, linkedin_url, tags
               FROM startup_leads
               WHERE email IS NOT NULL AND email != ''
                 AND email_status = 'not_contacted'
               ORDER BY company_name"""
        ).fetchall()
        lead_ids = []
        for lead in lead_rows:
            lead_emails = [e.strip().lower() for e in lead["email"].split(",")]
            if not any(e in sent_emails for e in lead_emails):
                lead_ids.append(-lead["id"])  # negative ID = startup lead
        post_ids = post_ids + lead_ids

    if not post_ids:
        with _generate_lock:
            generate_worker_state["running"] = False
        return {"status": "ok", "message": "No posts or leads to generate emails for."}

    # Cap at 200 per batch to avoid overloading the API and keep runs manageable
    MAX_BATCH = 200
    total_eligible = len(post_ids)
    post_ids = post_ids[:MAX_BATCH]

    from worker_ctx import current_uid, run_with_user
    threading.Thread(target=run_with_user(current_uid(), _bulk_generate_worker, post_ids), daemon=True).start()
    msg = f"Generating emails for {len(post_ids)} posts/leads in background..."
    if total_eligible > MAX_BATCH:
        msg += f" ({total_eligible - MAX_BATCH} remaining for next batch)"
    return {"status": "started", "message": msg, "total": len(post_ids)}


@router.post("/api/email/bulk-send")
def api_bulk_send(req: BulkSendRequest):
    """Start bulk email sending in background. Non-blocking."""
    with _send_lock:
        if send_worker_state["running"]:
            raise HTTPException(status_code=400, detail="Email sending already running. Wait or stop it first.")
        send_worker_state["running"] = True

    db_conn = _get_db()
    draft_count = db_conn.execute("SELECT COUNT(*) FROM email_outreach WHERE status='draft' AND subject IS NOT NULL").fetchone()[0]
    if draft_count == 0:
        with _send_lock:
            send_worker_state["running"] = False
        return {"status": "ok", "message": "No draft emails to send."}

    from worker_ctx import current_uid, run_with_user
    threading.Thread(target=run_with_user(current_uid(), _bulk_send_worker, req.attach_resume), daemon=True).start()
    return {"status": "started", "message": f"Sending {draft_count} emails in background...", "total": draft_count}


@router.get("/api/email/worker-status")
def api_email_worker_status():
    """Poll this to track bulk generate/send progress. Returns both workers."""
    def _snapshot(state, lock):
        with lock:
            return {
                "running": state["running"],
                "task": state["task"],
                "current": state["current"],
                "total": state["total"],
                "current_label": state["current_label"],
                "succeeded": state.get("succeeded", 0),
                "failed": state.get("failed", 0),
                "skipped": state.get("skipped", 0),
                "results": state["results"][-20:],
                "error": state.get("error"),
            }

    gen = _snapshot(generate_worker_state, _generate_lock)
    snd = _snapshot(send_worker_state, _send_lock)

    # Legacy compat: "running" is true if either worker is active
    running = gen["running"] or snd["running"]
    task = gen["task"] if gen["running"] else (snd["task"] if snd["running"] else None)

    result = {
        "running": running,
        "task": task,
        # Per-worker states for parallel UI
        "generate": gen,
        "send": snd,
        # Legacy flat fields (use active worker or generate as default)
        "current": gen["current"] if gen["running"] else snd["current"],
        "total": gen["total"] if gen["running"] else snd["total"],
        "current_label": gen["current_label"] if gen["running"] else snd["current_label"],
        "succeeded": gen["succeeded"] + snd["succeeded"],
        "failed": gen["failed"] + snd["failed"],
        "results": (gen["results"] + snd["results"])[-20:],
        "error": gen["error"] or snd["error"],
    }

    # Live draft count so the UI can update "Send All Drafts (N)" in real-time
    db_conn = _get_db()
    result["draft_count"] = db_conn.execute(
        "SELECT COUNT(*) FROM email_outreach WHERE status='draft' AND subject IS NOT NULL"
    ).fetchone()[0]

    # When neither is running, include last completed run so UI survives refresh/restart
    if not running:
        db_conn = _get_db()
        row = db_conn.execute(
            "SELECT worker_type, started_at, finished_at, status, succeeded, failed, total, results "
            "FROM worker_runs WHERE worker_type IN ('bulk_generate', 'bulk_send') "
            "ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        if row:
            result["last_run"] = dict(row)

    return result


@router.post("/api/email/worker-stop")
def api_email_worker_stop(task: Optional[str] = None):
    """Stop a running bulk operation. Pass task='generating' or 'sending' to stop one, or omit to stop both."""
    if task == "generating" or task is None:
        with _generate_lock:
            generate_worker_state["running"] = False
    if task == "sending" or task is None:
        with _send_lock:
            send_worker_state["running"] = False
    return {"status": "stopped", "stopped": task or "all"}


@router.get("/api/email/history")
def api_email_history():
    db_conn = _get_db()
    rows = db_conn.execute(
        """SELECT eo.id, eo.post_id, eo.recipient_email as to_email, eo.subject, eo.body,
                  eo.status, eo.sent_at, eo.created_at,
                  eo.variant, eo.variant_strategy, eo.outreach_type, eo.followup_count, eo.last_followup_at, eo.source, eo.phone, eo.hashtags,
                  p.author_name as to_name, p.author_headline, p.content as post_content,
                  p.links as post_links, p.post_url, p.domain_relevance, p.email as post_email,
                  (SELECT GROUP_CONCAT(j.role, ', ') FROM jobs j WHERE j.post_id = eo.post_id) as role,
                  (SELECT j2.company FROM jobs j2 WHERE j2.post_id = eo.post_id LIMIT 1) as company,
                  (SELECT j3.location FROM jobs j3 WHERE j3.post_id = eo.post_id LIMIT 1) as location
           FROM email_outreach eo
           LEFT JOIN posts p ON p.id = eo.post_id
           ORDER BY eo.created_at DESC
           LIMIT 200"""
    ).fetchall()
    return {"history": [dict(r) for r in rows], "total": len(rows)}


@router.get("/api/email/connections/{post_id}")
def api_email_connections(post_id: int):
    conn = _get_db()
    row = conn.execute("SELECT j.company FROM jobs j WHERE j.post_id = ?", (post_id,)).fetchone()
    if not row or not row["company"]:
        return {"has_connections": False, "company": "", "contacts": [], "recommendation": "cold_apply"}
    from services.referral_detector import find_connections
    return find_connections(conn, row["company"])


@router.post("/api/email/check-replies")
def api_check_replies():
    """Run a single IMAP check for replies."""
    from services.email_service import check_replies_once
    return check_replies_once()

@router.post("/api/email/check-bounces")
def api_check_bounces():
    """Scan inbox for bounce notifications and mark affected emails."""
    from services.email_service import check_replies_once
    # check_replies_once already includes bounce detection after the fix above
    return check_replies_once()

@router.post("/api/email/imap-start")
def api_imap_start():
    """Start continuous IMAP polling."""
    from services.email_service import start_imap_polling
    from worker_ctx import current_uid
    return start_imap_polling(user_id=current_uid())

@router.post("/api/email/imap-stop")
def api_imap_stop():
    """Stop IMAP polling."""
    from services.email_service import stop_imap_polling
    return stop_imap_polling()

@router.get("/api/email/imap-status")
def api_imap_status():
    """Get IMAP worker status."""
    from services.email_service import get_imap_status
    return get_imap_status()


@router.post("/api/email/deep-scan")
def api_deep_scan(since: str = "01-Mar-2026"):
    """Deep backfill scan for ALL missed replies since a date.
    Searches INBOX, All Mail, Important, and Spam folders.
    Use this to catch every reply you've missed."""
    from services.email_service import deep_scan_replies
    return deep_scan_replies(since_date=since)


@router.post("/api/email/reclassify")
def api_reclassify_replies():
    """Re-classify all existing replies with updated rejection/interest keywords.
    Run this after keyword patterns are updated to fix mis-classified replies."""
    from services.email_service import reclassify_replies
    return reclassify_replies()


@router.post("/api/email/scan-offers")
def api_scan_offers(since: str = "01-Apr-2026"):
    """Scan the mailbox for job-offer emails and advance matching pipeline leads to 'offer'.
    Matches by sender DOMAIN, so an offer from a different person at a known company
    (e.g. an HR/founder address rather than the outreach address) is still detected.
    Generic providers (gmail/outlook/…) and your own sent mail are excluded."""
    from services.email_service import scan_offers
    return scan_offers(since_date=since)


@router.post("/api/email/scan-interviews")
def api_scan_interviews(since: str = "01-Apr-2026"):
    """Scan the mailbox for interview emails and advance matching leads to 'interviewing'.
    Same domain-aware matching as scan-offers. Forward-only: never downgrades a lead
    already at offer/rejected/interviewing."""
    from services.email_service import scan_interviews
    return scan_interviews(since_date=since)


@router.get("/api/email/reply-breakdown")
def api_reply_breakdown():
    """Detailed breakdown of all replies by type, with previews."""
    conn = _get_db()
    replies = conn.execute(
        "SELECT id, recipient_email, subject, reply_type, reply_preview, reply_detected_at, sent_at "
        "FROM email_outreach WHERE status = 'replied' ORDER BY reply_detected_at DESC"
    ).fetchall()
    breakdown = {"interested": [], "rejection": [], "auto_reply": [], "info": []}
    for r in replies:
        entry = {
            "id": r["id"],
            "to": r["recipient_email"],
            "subject": r["subject"],
            "reply_preview": r["reply_preview"],
            "reply_detected_at": r["reply_detected_at"],
            "sent_at": r["sent_at"],
        }
        rtype = r["reply_type"] or "info"
        breakdown.setdefault(rtype, []).append(entry)
    return {
        "total_replies": len(replies),
        "interested": len(breakdown.get("interested", [])),
        "rejection": len(breakdown.get("rejection", [])),
        "auto_reply": len(breakdown.get("auto_reply", [])),
        "info": len(breakdown.get("info", [])),
        "breakdown": breakdown,
    }


@router.get("/api/email/stats")
def api_email_stats():
    """Comprehensive email delivery stats."""
    conn = _get_db()

    total = conn.execute("SELECT COUNT(*) FROM email_outreach").fetchone()[0]
    sent = conn.execute("SELECT COUNT(*) FROM email_outreach WHERE status = 'sent'").fetchone()[0]
    failed = conn.execute("SELECT COUNT(*) FROM email_outreach WHERE status = 'failed'").fetchone()[0]
    replied = conn.execute("SELECT COUNT(*) FROM email_outreach WHERE status = 'replied'").fetchone()[0]
    draft = conn.execute("SELECT COUNT(*) FROM email_outreach WHERE status IN ('draft', 'pending')").fetchone()[0]

    delivered = sent + replied  # sent or replied = successfully delivered

    bounced = conn.execute("SELECT COUNT(*) FROM email_outreach WHERE error_type = 'bounced'").fetchone()[0]

    # Error breakdown
    errors = {}
    for row in conn.execute("SELECT error_type, COUNT(*) as cnt FROM email_outreach WHERE status='failed' AND error_type IS NOT NULL GROUP BY error_type").fetchall():
        errors[row[0]] = row[1]

    # Recent failures
    recent_failures = []
    for row in conn.execute(
        "SELECT recipient_email, error_type, error_message, created_at FROM email_outreach "
        "WHERE status='failed' ORDER BY created_at DESC LIMIT 10"
    ).fetchall():
        recent_failures.append({
            "email": row[0], "error_type": row[1], "error_message": row[2], "date": row[3]
        })

    # Worker history
    worker_history = []
    try:
        for row in conn.execute(
            "SELECT worker_type, started_at, finished_at, status, total, succeeded, failed "
            "FROM worker_runs ORDER BY started_at DESC LIMIT 10"
        ).fetchall():
            worker_history.append({
                "type": row[0], "started_at": row[1], "finished_at": row[2],
                "status": row[3], "total": row[4], "succeeded": row[5], "failed": row[6]
            })
    except Exception:
        pass  # table might not exist yet

    # Bounce-blocked domains (auto-blocked from bounce history)
    bounce_blocked = get_bounce_blocked_domains(conn)

    # Top bouncing domains with counts
    top_bounce_domains = []
    for row in conn.execute(
        """SELECT SUBSTR(
            CASE WHEN recipient_email LIKE '%,%'
                 THEN TRIM(SUBSTR(recipient_email, 1, INSTR(recipient_email, ',') - 1))
                 ELSE TRIM(recipient_email)
            END,
            INSTR(
                CASE WHEN recipient_email LIKE '%,%'
                     THEN TRIM(SUBSTR(recipient_email, 1, INSTR(recipient_email, ',') - 1))
                     ELSE TRIM(recipient_email)
                END, '@') + 1
           ) as domain,
           COUNT(*) as cnt
           FROM email_outreach
           WHERE error_type = 'bounced'
           GROUP BY domain ORDER BY cnt DESC LIMIT 15"""
    ).fetchall():
        top_bounce_domains.append({"domain": row[0], "bounces": row[1]})

    # Reply type breakdown
    reply_types = {}
    for row in conn.execute(
        "SELECT reply_type, COUNT(*) as cnt FROM email_outreach WHERE status='replied' AND reply_type IS NOT NULL GROUP BY reply_type"
    ).fetchall():
        reply_types[row[0]] = row[1]

    # Unreplied emails older than 3 days (potential missed replies)
    unreplied_old = conn.execute(
        "SELECT COUNT(*) FROM email_outreach WHERE status='sent' AND reply_detected_at IS NULL AND sent_at < datetime('now', '-3 days')"
    ).fetchone()[0]

    return {
        "total": total,
        "delivered": delivered,
        "sent": sent,
        "failed": failed,
        "replied": replied,
        "draft": draft,
        "bounced": bounced,
        "bounce_rate": f"{(bounced / max(sent + bounced, 1) * 100):.1f}%",
        "delivery_rate": f"{(delivered / max(delivered + failed, 1) * 100):.1f}%",
        "reply_rate": f"{(replied / max(delivered, 1) * 100):.1f}%",
        "reply_types": reply_types,
        "unreplied_awaiting_scan": unreplied_old,
        "errors": errors,
        "recent_failures": recent_failures,
        "worker_history": worker_history,
        "bounce_blocked_domains": bounce_blocked,
        "top_bounce_domains": top_bounce_domains,
    }


@router.post("/api/email/classify-failures")
def api_classify_failures():
    """One-time: classify existing failed emails by checking address format."""
    import re
    conn = _get_db()
    unclassified = conn.execute(
        "SELECT id, recipient_email FROM email_outreach WHERE status='failed' AND error_type IS NULL"
    ).fetchall()

    classified = 0
    for row in unclassified:
        email = row[1] or ""
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            conn.execute("UPDATE email_outreach SET error_type='invalid_address', error_message='Invalid email format' WHERE id=?", (row[0],))
        else:
            conn.execute("UPDATE email_outreach SET error_type='unknown', error_message='Historical failure - reason not recorded' WHERE id=?", (row[0],))
        classified += 1

    conn.commit()
    return {"classified": classified}


@router.get("/api/email/address-quality")
def api_address_quality():
    """Report on email address quality issues."""
    conn = _get_db()

    # Multi-address
    multi = conn.execute(
        "SELECT id, recipient_email, subject, status FROM email_outreach WHERE recipient_email LIKE '%,%' ORDER BY created_at DESC"
    ).fetchall()

    # Generic addresses
    generic = conn.execute(
        "SELECT id, recipient_email, status FROM email_outreach "
        "WHERE recipient_email LIKE 'info@%' OR recipient_email LIKE 'careers@%' "
        "OR recipient_email LIKE 'hr@%' OR recipient_email LIKE 'support@%' "
        "OR recipient_email LIKE 'contact@%' OR recipient_email LIKE 'hello@%' "
        "OR recipient_email LIKE 'jobs@%' OR recipient_email LIKE 'team@%' "
        "ORDER BY created_at DESC"
    ).fetchall()

    # Bounced
    bounced = conn.execute(
        "SELECT id, recipient_email, error_message FROM email_outreach WHERE error_type = 'bounced'"
    ).fetchall()

    return {
        "multi_address": [{"id": r[0], "email": r[1], "subject": r[2], "status": r[3]} for r in multi],
        "multi_count": len(multi),
        "generic": [{"id": r[0], "email": r[1], "status": r[2]} for r in generic],
        "generic_count": len(generic),
        "bounced": [{"id": r[0], "email": r[1], "error": r[2]} for r in bounced],
        "bounced_count": len(bounced),
    }


@router.get("/api/email/send-time-stats")
def api_send_time_stats():
    """Analyze reply rates by send hour and day of week."""
    conn = _get_db()

    # By hour of day
    hourly = []
    for row in conn.execute("""
        SELECT CAST(strftime('%H', sent_at) AS INTEGER) as hour,
               COUNT(*) as sent,
               SUM(CASE WHEN status='replied' THEN 1 ELSE 0 END) as replied
        FROM email_outreach
        WHERE sent_at IS NOT NULL AND status IN ('sent', 'replied')
        GROUP BY hour ORDER BY hour
    """).fetchall():
        hourly.append({"hour": row[0], "sent": row[1], "replied": row[2],
                       "rate": round(row[2]/max(row[1],1)*100, 1)})

    # By day of week (0=Sunday, 6=Saturday)
    daily = []
    day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    for row in conn.execute("""
        SELECT CAST(strftime('%w', sent_at) AS INTEGER) as dow,
               COUNT(*) as sent,
               SUM(CASE WHEN status='replied' THEN 1 ELSE 0 END) as replied
        FROM email_outreach
        WHERE sent_at IS NOT NULL AND status IN ('sent', 'replied')
        GROUP BY dow ORDER BY dow
    """).fetchall():
        daily.append({"day": day_names[row[0]], "sent": row[1], "replied": row[2],
                      "rate": round(row[2]/max(row[1],1)*100, 1)})

    # Best time recommendation
    best_hour = max(hourly, key=lambda x: x['rate']) if hourly else None
    best_day = max(daily, key=lambda x: x['rate']) if daily else None

    return {
        "hourly": hourly,
        "daily": daily,
        "recommendation": {
            "best_hour": best_hour['hour'] if best_hour else None,
            "best_day": best_day['day'] if best_day else None,
            "best_hour_rate": best_hour['rate'] if best_hour else 0,
            "best_day_rate": best_day['rate'] if best_day else 0,
        }
    }


@router.post("/api/email/update-status")
def api_update_email_status(req: dict):
    """Manually update an email's status (e.g., mark as replied, bounced)."""
    conn = _get_db()
    outreach_id = req.get("outreach_id")
    new_status = req.get("status")
    if not outreach_id or new_status not in ("sent", "replied", "failed", "draft", "bounced"):
        return {"error": "Invalid outreach_id or status"}
    conn.execute("UPDATE email_outreach SET status = ? WHERE id = ?", (new_status, outreach_id))
    conn.commit()
    return {"status": "updated", "outreach_id": outreach_id, "new_status": new_status}


@router.get("/api/email/config-status")
def api_email_config_status():
    configured = bool(SMTP_CONFIG["password"] and SMTP_CONFIG["user"])
    return {
        "configured": configured,
        "smtp_host": SMTP_CONFIG["host"],
        "from_email": SMTP_CONFIG["from_email"],
        "from_name": SMTP_CONFIG["from_name"],
    }
