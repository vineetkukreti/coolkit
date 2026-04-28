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
    generate_email,
    send_email,
    is_email_blocked,
    _bulk_generate_worker,
    _bulk_send_worker,
    validate_email_before_send,
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
        result = generate_email(post_data)
        return {"status": "ok", "post_id": req.post_id, **result}
    except Exception as e:
        print(f"Error in /api/email/generate: {e}")
        raise HTTPException(status_code=500, detail="Email generation failed. Please try again.")


@router.post("/api/email/send")
def api_send_email(req: EmailSendRequest):
    db_conn = _get_db()
    # Check blocklist — also look up company from DB if post_id given
    company = ""
    if req.post_id:
        row = db_conn.execute("SELECT company FROM jobs WHERE post_id = ? LIMIT 1", (req.post_id,)).fetchone()
        if row:
            company = row["company"] or ""
    if is_email_blocked(req.to_email, company):
        raise HTTPException(status_code=400, detail="Blocked: this email belongs to your current employer (Southguild). Cannot send outreach.")
    check = validate_email_before_send(req.to_email)
    if not check["valid"]:
        raise HTTPException(status_code=400, detail=check["reason"])
    pid = req.post_id if req.post_id else None  # NULL for FK safety when no real post
    try:
        result = send_email(req.to_email, req.subject, req.body, attach_resume=req.attach_resume)
        if result["status"] == "sent":
            db_conn.execute(
                """INSERT INTO email_outreach (post_id, recipient_email, subject, body, status, sent_at)
                   VALUES (?, ?, ?, ?, 'sent', datetime('now'))""",
                (pid, req.to_email, req.subject, req.body),
            )
            db_conn.commit()
            return {"status": "sent", "message": f"Email sent to {req.to_email}"}
        else:
            db_conn.execute(
                """INSERT INTO email_outreach (post_id, recipient_email, subject, body, status, error_message, error_type)
                   VALUES (?, ?, ?, ?, 'failed', ?, ?)""",
                (pid, req.to_email, req.subject, req.body, result.get("error_message", "")[:500], result.get("error_type", "unknown")),
            )
            db_conn.commit()
            raise HTTPException(status_code=500, detail=result.get("error_message", "Send failed"))
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /api/email/send: {e}")
        try:
            db_conn.execute(
                """INSERT INTO email_outreach (post_id, recipient_email, subject, body, status, error_message, error_type)
                   VALUES (?, ?, ?, ?, 'failed', ?, 'unknown')""",
                (pid, req.to_email, req.subject, req.body, str(e)[:500]),
            )
            db_conn.commit()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Email sending failed. Please try again.")


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
                  eo.variant, eo.variant_strategy, eo.outreach_type, eo.followup_count, eo.last_followup_at,
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
    return start_imap_polling()

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

    return {
        "total": total,
        "delivered": delivered,
        "sent": sent,
        "failed": failed,
        "replied": replied,
        "draft": draft,
        "bounced": bounced,
        "delivery_rate": f"{(delivered / max(delivered + failed, 1) * 100):.1f}%",
        "reply_rate": f"{(replied / max(delivered, 1) * 100):.1f}%",
        "errors": errors,
        "recent_failures": recent_failures,
        "worker_history": worker_history,
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
