"""Email outreach routes — generate, send, bulk operations, and history."""

import random
import threading
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import init_db
from services.email_service import (
    email_worker_state,
    _email_lock,
    _generate_email_with_gemini,
    _send_email_smtp,
    _is_blocked_email,
    _bulk_generate_worker,
    _bulk_send_worker,
    SMTP_CONFIG,
)

router = APIRouter()

_local = threading.local()


def _get_db():
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = init_db()
    return _local.conn


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


class BulkEmailRequest(BaseModel):
    post_ids: list[int]


class SaveDraftRequest(BaseModel):
    post_id: int
    to_email: str
    subject: str
    body: str


class BulkSendRequest(BaseModel):
    attach_resume: bool = True


# ───────────────────────────────────────────────
# Routes
# ───────────────────────────────────────────────

@router.post("/api/email/save-draft")
def api_save_draft(req: SaveDraftRequest):
    """Save or update a draft email for a post."""
    db_conn = _get_db()
    existing = db_conn.execute(
        "SELECT id FROM email_outreach WHERE post_id = ? AND status = 'draft'",
        (req.post_id,),
    ).fetchone()
    if existing:
        db_conn.execute(
            """UPDATE email_outreach SET recipient_email=?, subject=?, body=?,
               created_at=datetime('now') WHERE id=?""",
            (req.to_email, req.subject, req.body, existing["id"]),
        )
    else:
        db_conn.execute(
            """INSERT INTO email_outreach (post_id, recipient_email, subject, body, status)
               VALUES (?, ?, ?, ?, 'draft')""",
            (req.post_id, req.to_email, req.subject, req.body),
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
        result = _generate_email_with_gemini(post_data)
        return {"status": "ok", "post_id": req.post_id, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email generation failed: {str(e)}")


@router.post("/api/email/send")
def api_send_email(req: EmailSendRequest):
    db_conn = _get_db()
    # Check blocklist — also look up company from DB if post_id given
    company = ""
    if req.post_id:
        row = db_conn.execute("SELECT company FROM jobs WHERE post_id = ? LIMIT 1", (req.post_id,)).fetchone()
        if row:
            company = row["company"] or ""
    if _is_blocked_email(req.to_email, company):
        raise HTTPException(status_code=400, detail="Blocked: this email belongs to your current employer (Southguild). Cannot send outreach.")
    pid = req.post_id if req.post_id else None  # NULL for FK safety when no real post
    try:
        _send_email_smtp(req.to_email, req.subject, req.body, attach_resume=req.attach_resume)
        db_conn.execute(
            """INSERT INTO email_outreach (post_id, recipient_email, subject, body, status, sent_at)
               VALUES (?, ?, ?, ?, 'sent', datetime('now'))""",
            (pid, req.to_email, req.subject, req.body),
        )
        db_conn.commit()
        return {"status": "sent", "message": f"Email sent to {req.to_email}"}
    except Exception as e:
        try:
            db_conn.execute(
                """INSERT INTO email_outreach (post_id, recipient_email, subject, body, status)
                   VALUES (?, ?, ?, ?, 'failed')""",
                (pid, req.to_email, req.subject, req.body),
            )
            db_conn.commit()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/email/bulk-generate")
def api_bulk_generate(req: BulkEmailRequest):
    """Start bulk email generation in background. Non-blocking."""
    with _email_lock:
        if email_worker_state["running"]:
            raise HTTPException(status_code=400, detail=f"Email worker already running ({email_worker_state['task']}). Wait or stop it first.")

    db_conn = _get_db()
    # If no post_ids given, auto-select all outreach-ready posts without drafts
    post_ids = req.post_ids
    if not post_ids:
        rows = db_conn.execute(
            """SELECT p.id FROM posts p
               WHERE p.email IS NOT NULL AND p.email != ''
                 AND p.is_hiring = 1
                 AND LOWER(p.email) NOT LIKE '%southguild%'
                 AND p.id NOT IN (SELECT post_id FROM email_outreach WHERE post_id IS NOT NULL AND status IN ('sent', 'draft'))
                 AND NOT EXISTS (
                     SELECT 1 FROM email_outreach eo
                     WHERE eo.status = 'sent'
                       AND INSTR(p.email, eo.recipient_email) > 0
                 )
               ORDER BY CASE p.domain_relevance WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END
            """
        ).fetchall()
        post_ids = [r["id"] for r in rows]

    if not post_ids:
        return {"status": "ok", "message": "No posts to generate emails for."}

    threading.Thread(target=_bulk_generate_worker, args=(post_ids,), daemon=True).start()
    return {"status": "started", "message": f"Generating emails for {len(post_ids)} posts in background...", "total": len(post_ids)}


@router.post("/api/email/bulk-send")
def api_bulk_send(req: BulkSendRequest):
    """Start bulk email sending in background. Non-blocking."""
    with _email_lock:
        if email_worker_state["running"]:
            raise HTTPException(status_code=400, detail=f"Email worker already running ({email_worker_state['task']}). Wait or stop it first.")

    db_conn = _get_db()
    draft_count = db_conn.execute("SELECT COUNT(*) FROM email_outreach WHERE status='draft' AND subject IS NOT NULL").fetchone()[0]
    if draft_count == 0:
        return {"status": "ok", "message": "No draft emails to send."}

    threading.Thread(target=_bulk_send_worker, args=(req.attach_resume,), daemon=True).start()
    return {"status": "started", "message": f"Sending {draft_count} emails in background...", "total": draft_count}


@router.get("/api/email/worker-status")
def api_email_worker_status():
    """Poll this to track bulk generate/send progress."""
    with _email_lock:
        sent_ok = sum(1 for r in email_worker_state["results"] if r.get("status") in ("ok", "sent"))
        failed = sum(1 for r in email_worker_state["results"] if r.get("status") in ("error", "failed"))
        return {
            "running": email_worker_state["running"],
            "task": email_worker_state["task"],
            "current": email_worker_state["current"],
            "total": email_worker_state["total"],
            "current_label": email_worker_state["current_label"],
            "succeeded": sent_ok,
            "failed": failed,
            "results": email_worker_state["results"][-20:],  # last 20 for UI
        }


@router.post("/api/email/worker-stop")
def api_email_worker_stop():
    """Stop the running bulk operation."""
    with _email_lock:
        email_worker_state["running"] = False
    return {"status": "stopped"}


@router.get("/api/email/history")
def api_email_history():
    db_conn = _get_db()
    rows = db_conn.execute(
        """SELECT eo.id, eo.post_id, eo.recipient_email as to_email, eo.subject, eo.body,
                  eo.status, eo.sent_at, eo.created_at,
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


@router.get("/api/email/config-status")
def api_email_config_status():
    configured = bool(SMTP_CONFIG["password"] and SMTP_CONFIG["user"])
    return {
        "configured": configured,
        "smtp_host": SMTP_CONFIG["host"],
        "from_email": SMTP_CONFIG["from_email"],
        "from_name": SMTP_CONFIG["from_name"],
    }
