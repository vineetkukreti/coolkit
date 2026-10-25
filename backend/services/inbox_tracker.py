"""Inbox Tracker — auto-detect application status from incoming emails."""

import re
import imaplib
import email as email_lib
from email.header import decode_header
from datetime import datetime, timedelta
import os
import json
import threading
import time

from db import init_db

IMAP_CONFIG = {
    "host": os.getenv("IMAP_HOST", "imap.gmail.com"),
    "port": int(os.getenv("IMAP_PORT", "993")),
    "user": os.getenv("IMAP_USER", "") or os.getenv("SMTP_USER", ""),
    "password": os.getenv("IMAP_PASSWORD", "") or os.getenv("SMTP_PASSWORD", ""),
}

# Patterns to classify incoming emails
CONFIRMATION_PATTERNS = [
    "application received", "application has been received",
    "thank you for applying", "thanks for applying",
    "we received your application", "application submitted",
    "successfully applied", "application confirmation",
    "your application for", "we have received your resume",
    "application to", "thank you for your interest in",
    "we appreciate your interest", "your submission",
]

REJECTION_PATTERNS = [
    "unfortunately", "regret to inform",
    "not moving forward", "will not be moving forward",
    "decided to pursue other", "decided to move forward with other",
    "not selected", "not been selected",
    "position has been filled", "role has been filled",
    "not a fit", "not the right fit",
    "we will not be proceeding", "unable to offer",
    "after careful consideration", "competitive pool of candidates",
    "keep your resume on file", "future openings",
    "wish you the best", "best of luck",
    "we regret", "not able to move forward",
]

OFFER_PATTERNS = [
    "offer letter", "letter of offer", "offer of employment",
    "pleased to offer", "happy to offer", "delighted to offer",
    "excited to offer", "we would like to offer", "would like to offer you",
    "extend an offer", "extend a formal offer", "formal offer",
    "offer you the position", "offer you the role",
    "compensation package", "compensation figure", "annual ctc", "your ctc", "ctc of",
    "date of joining", "joining date", "welcome aboard",
    "welcome to the team", "you have been selected for",
    "release your offer", "rolling out your offer",
    # Indian offer / pre-offer vocabulary
    "salary structure", "proposed salary structure", "revised salary",
    "salary breakup", "house rent allowance", "letter of intent",
    "letter of appointment", "letter of engagement", "(loi)", "(loe)",
    # Founding / startup equity offer vocabulary
    "fully diluted", "vesting", "esop", "stock options",
]

INTERVIEW_PATTERNS = [
    "schedule an interview", "interview invitation", "interview",
    "like to schedule", "book a time", "book a slot",
    "phone screen", "phone interview", "video interview", "video call",
    "technical assessment", "technical round", "coding challenge", "coding round",
    "online assessment", "aptitude test", "assessment round",
    "meet the team", "next steps in the process", "next round", "first round",
    "we'd like to invite you", "would like to invite you", "love to chat",
    "availability for", "your availability", "calendly", "schedule a call",
    "hiring manager would like", "round of interviews",
    "shortlisted", "shortlisting", "hr round", "managerial round",
    "zoom meeting", "google meet", "ms teams", "teams meeting",
    # Job-portal / recruiter invitation vocabulary
    "job invite", "job invitation", "recruiter has invited", "invited you for", "invited you to",
    "has invited you", "selected for interview", "selected for the role", "moved to the next stage",
    "chat regarding", "discussion regarding", "conversation about", "talk about the role",
    "meet with the team", "meet the team", "hiring manager would like",
]

# Companies that send automated application emails (from career portals and job boards)
CAREER_PORTAL_SENDERS = [
    "noreply@", "no-reply@", "careers@", "jobs@", "talent@",
    "recruiting@", "hiring@", "hr@", "applications@",
    "workday", "greenhouse", "lever", "icims", "taleo",
    "smartrecruiters", "jobvite", "ashby", "bamboohr",
    # Indian/global job boards and recruiter platforms
    "naukri.com", "naukri", "linkedin.com", "linkedin", "indeed", "glassdoor",
    "wellfound", "angel.co", "internshala", "shine", "monster", "bayt",
    "iimjobs", "hirist", "foundit", "timesjobs", "simplyhired",
]


def _decode_header(value):
    if not value:
        return ""
    decoded = decode_header(value)
    parts = []
    for part, charset in decoded:
        if isinstance(part, bytes):
            parts.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(part)
    return " ".join(parts)


def _extract_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="replace")
                break
            elif part.get_content_type() == "text/html" and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    raw = payload.decode("utf-8", errors="replace")
                    body = re.sub(r'<[^>]+>', ' ', raw)
                    body = re.sub(r'\s+', ' ', body).strip()
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="replace")
    return body


def classify_inbox_email(subject: str, body: str, from_addr: str) -> dict:
    """Classify an incoming email as confirmation, rejection, interview, or irrelevant."""
    text = (subject + " " + body).lower()
    from_lower = from_addr.lower()

    # Check if it's from a career portal
    is_career_portal = any(p in from_lower for p in CAREER_PORTAL_SENDERS)

    # Check patterns (order matters: rejection > offer > interview > confirmation).
    # Rejection first so "unable to offer" isn't mistaken for an offer; offer before
    # interview so an offer email isn't downgraded to an interview invite.
    if any(p in text for p in REJECTION_PATTERNS):
        return {"type": "rejection", "confidence": "high" if sum(1 for p in REJECTION_PATTERNS if p in text) >= 2 else "medium"}

    if any(p in text for p in OFFER_PATTERNS):
        return {"type": "offer", "confidence": "high" if sum(1 for p in OFFER_PATTERNS if p in text) >= 2 else "medium"}

    if any(p in text for p in INTERVIEW_PATTERNS):
        return {"type": "interview", "confidence": "high" if sum(1 for p in INTERVIEW_PATTERNS if p in text) >= 2 else "medium"}

    if any(p in text for p in CONFIRMATION_PATTERNS):
        return {"type": "confirmation", "confidence": "high" if is_career_portal else "medium"}

    if is_career_portal:
        return {"type": "unknown_career", "confidence": "low"}

    return {"type": "irrelevant", "confidence": "high"}


def _match_to_application(conn, from_addr: str, subject: str, body: str) -> dict | None:
    """Try to match an inbox email to an existing application."""
    text = (subject + " " + body).lower()

    # Strategy 1: Match by company name in applications table
    apps = conn.execute(
        "SELECT id, post_id, job_title, company, status, outcome, applied_at FROM applications WHERE status = 'applied' ORDER BY applied_at DESC"
    ).fetchall()

    for app in apps:
        company = (app["company"] or "").lower()
        job_title = (app["job_title"] or "").lower()
        # Whole-word match so "Meta" doesn't match "metadata"
        if company and len(company) > 2 and re.search(rf"\b{re.escape(company)}\b", text):
            return dict(app)
        if job_title and len(job_title) > 5 and re.search(rf"\b{re.escape(job_title)}\b", text):
            return dict(app)

    # Strategy 2: Match by domain in from_addr
    if "@" in from_addr:
        domain = from_addr.split("@")[1].split(".")[0].lower()
        if len(domain) > 3:
            for app in apps:
                company = (app["company"] or "").lower().replace(" ", "")
                if domain in company or company in domain:
                    return dict(app)

    return None


# Outcome on applications.outcome only ever moves up this ladder
_OUTCOME_RANK = {None: 0, "interviewing": 1, "rejected": 2, "offer": 3}
_TYPE_TO_OUTCOME = {"interview": "interviewing", "rejection": "rejected", "offer": "offer"}
_TYPE_TO_STAGE = {"interview": "interviewing", "rejection": "rejected", "offer": "offer"}
_STAGE_RANK = {"applied": 0, "replied": 1, "interviewing": 2, "rejected": 3, "offer": 4}


def _ensure_job_emails_table(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS job_emails (
               id              INTEGER PRIMARY KEY AUTOINCREMENT,
               message_id      TEXT UNIQUE,
               from_addr       TEXT,
               subject         TEXT,
               preview         TEXT,
               type            TEXT,
               confidence      TEXT,
               application_id  INTEGER REFERENCES applications(id) ON DELETE SET NULL,
               company         TEXT,
               received_at     TEXT,
               handled         INTEGER DEFAULT 0,
               created_at      TEXT DEFAULT (datetime('now'))
           )"""
    )


def record_job_email(conn, message_id: str, from_addr: str, subject: str, body: str,
                     received_at: str = "") -> dict | None:
    """Classify one email, store it, and advance the matched application/pipeline lead.

    Returns the stored entry, or None if the email isn't job-related or was already recorded.
    """
    _ensure_job_emails_table(conn)
    classification = classify_inbox_email(subject, body, from_addr)
    if classification["type"] not in ("rejection", "offer", "interview", "confirmation"):
        return None
    if message_id and conn.execute("SELECT 1 FROM job_emails WHERE message_id = ?", (message_id,)).fetchone():
        return None

    matched = _match_to_application(conn, from_addr, subject, body)
    conn.execute(
        """INSERT INTO job_emails (message_id, from_addr, subject, preview, type, confidence,
                                   application_id, company, received_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (message_id or None, from_addr, subject, body[:2000], classification["type"], classification["confidence"],
         matched["id"] if matched else None, matched["company"] if matched else None, received_at),
    )

    if matched and classification["confidence"] in ("high", "medium"):
        outcome = _TYPE_TO_OUTCOME.get(classification["type"])
        if outcome and _OUTCOME_RANK[outcome] > _OUTCOME_RANK.get(matched.get("outcome"), 0):
            conn.execute("UPDATE applications SET outcome = ? WHERE id = ?", (outcome, matched["id"]))
        stage = _TYPE_TO_STAGE.get(classification["type"])
        if stage and matched.get("post_id"):
            lead = conn.execute("SELECT id, stage FROM pipeline_leads WHERE post_id = ?", (matched["post_id"],)).fetchone()
            if lead and _STAGE_RANK[stage] > _STAGE_RANK.get(lead["stage"], 0):
                conn.execute("UPDATE pipeline_leads SET stage = ?, updated_at = datetime('now') WHERE id = ?",
                             (stage, lead["id"]))
    conn.commit()
    return {"from": from_addr, "subject": subject, "type": classification["type"],
            "confidence": classification["confidence"], "body_preview": body[:200], "matched_application": matched}


def scan_inbox(since_date: str = None, limit: int = 200) -> dict:
    """Scan inbox for application-related emails, store them, and auto-update statuses."""
    imap_user = IMAP_CONFIG["user"]
    imap_pass = IMAP_CONFIG["password"]

    if not imap_user or not imap_pass:
        return {"status": "error", "error": "IMAP credentials not configured"}

    if since_date is None:
        dt = datetime.now() - timedelta(days=14)
        since_date = dt.strftime("%d-%b-%Y")

    conn = init_db()
    results = []
    updated = {"confirmations": 0, "rejections": 0, "interviews": 0, "offers": 0}
    counter_key = {"confirmation": "confirmations", "rejection": "rejections", "interview": "interviews", "offer": "offers"}
    msg_ids = []

    try:
        mail = imaplib.IMAP4_SSL(IMAP_CONFIG["host"], IMAP_CONFIG["port"], timeout=30)
        mail.login(imap_user, imap_pass)
        mail.select("INBOX", readonly=True)

        status, data = mail.search(None, f'(SINCE {since_date})')
        if status != "OK" or not data[0]:
            return {"status": "ok", "scanned": 0, "found": [], "updated": updated}

        # Most recent first
        msg_ids = list(reversed(data[0].split()[-limit:]))

        for msg_id in msg_ids:
            try:
                status, msg_data = mail.fetch(msg_id, "(RFC822.HEADER)")
                if status != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                    continue
                header = email_lib.message_from_bytes(msg_data[0][1])
                from_addr = _decode_header(header.get("From", "")).lower()
                subject = _decode_header(header.get("Subject", ""))

                # Cheap pre-filter on headers only — the body isn't fetched yet.
                is_career_portal = any(p in from_addr for p in CAREER_PORTAL_SENDERS)
                subject_lower = subject.lower()
                has_signal = any(p in subject_lower for p in
                                 INTERVIEW_PATTERNS + OFFER_PATTERNS + REJECTION_PATTERNS + CONFIRMATION_PATTERNS)
                if not is_career_portal and not has_signal:
                    continue

                status2, full_data = mail.fetch(msg_id, "(RFC822)")
                if status2 != "OK" or not full_data or not isinstance(full_data[0], tuple):
                    continue
                full_msg = email_lib.message_from_bytes(full_data[0][1])
                body = _extract_body(full_msg)[:2000]

                entry = record_job_email(conn, header.get("Message-ID", "").strip(), from_addr, subject, body,
                                         header.get("Date", ""))
                if entry:
                    results.append(entry)
                    if entry["matched_application"]:
                        updated[counter_key[entry["type"]]] += 1
            except Exception as exc:
                print(f"[inbox] skipped message {msg_id!r}: {exc}")
                continue

        mail.close()
        mail.logout()

    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        conn.close()

    return {
        "status": "ok",
        "scanned": len(msg_ids),
        "found": results,
        "updated": updated,
    }


def list_job_emails(conn, email_type: str = "", include_handled: bool = False, limit: int = 200) -> list:
    _ensure_job_emails_table(conn)
    sql = """SELECT e.*, a.job_title, a.job_url FROM job_emails e
             LEFT JOIN applications a ON a.id = e.application_id WHERE 1 = 1"""
    args = []
    if email_type:
        sql += " AND e.type = ?"
        args.append(email_type)
    if not include_handled:
        sql += " AND e.handled = 0"
    sql += " ORDER BY e.id DESC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def set_job_email_handled(conn, email_id: int, handled: bool = True) -> bool:
    _ensure_job_emails_table(conn)
    cur = conn.execute("UPDATE job_emails SET handled = ? WHERE id = ?", (int(handled), email_id))
    conn.commit()
    return cur.rowcount > 0
