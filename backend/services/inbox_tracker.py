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

INTERVIEW_PATTERNS = [
    "schedule an interview", "interview invitation",
    "like to schedule", "book a time",
    "phone screen", "video interview",
    "technical assessment", "coding challenge",
    "meet the team", "next steps in the process",
    "we'd like to invite you", "love to chat",
    "availability for", "calendly", "schedule a call",
    "hiring manager would like", "round of interviews",
]

# Companies that send automated application emails (from career portals)
CAREER_PORTAL_SENDERS = [
    "noreply@", "no-reply@", "careers@", "jobs@", "talent@",
    "recruiting@", "hiring@", "hr@", "applications@",
    "workday", "greenhouse", "lever", "icims", "taleo",
    "smartrecruiters", "jobvite", "ashby", "bamboohr",
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

    # Check patterns (order matters: rejection > interview > confirmation)
    if any(p in text for p in REJECTION_PATTERNS):
        return {"type": "rejection", "confidence": "high" if sum(1 for p in REJECTION_PATTERNS if p in text) >= 2 else "medium"}

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
        "SELECT id, post_id, job_title, company, status, applied_at FROM applications WHERE status = 'applied' ORDER BY applied_at DESC"
    ).fetchall()

    for app in apps:
        company = (app["company"] or "").lower()
        job_title = (app["job_title"] or "").lower()
        if company and len(company) > 2 and company in text:
            return dict(app)
        if job_title and len(job_title) > 5 and job_title in text:
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


def scan_inbox(since_date: str = None, limit: int = 200) -> dict:
    """Scan inbox for application-related emails and auto-update statuses."""
    imap_user = IMAP_CONFIG["user"]
    imap_pass = IMAP_CONFIG["password"]

    if not imap_user or not imap_pass:
        return {"status": "error", "error": "IMAP credentials not configured"}

    if since_date is None:
        dt = datetime.now() - timedelta(days=14)
        since_date = dt.strftime("%d-%b-%Y")

    conn = init_db()

    try:
        mail = imaplib.IMAP4_SSL(IMAP_CONFIG["host"], IMAP_CONFIG["port"], timeout=30)
        mail.login(imap_user, imap_pass)
        mail.select("INBOX", readonly=True)

        # Search for recent emails
        status, data = mail.search(None, f'(SINCE {since_date})')
        if status != "OK" or not data[0]:
            return {"status": "ok", "scanned": 0, "found": []}

        msg_ids = data[0].split()
        # Process most recent first
        msg_ids = list(reversed(msg_ids[-limit:]))

        results = []
        updated = {"confirmations": 0, "rejections": 0, "interviews": 0}

        for msg_id in msg_ids:
            try:
                status, msg_data = mail.fetch(msg_id, "(RFC822.HEADER)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue

                raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
                if not isinstance(raw, bytes):
                    continue

                msg = email_lib.message_from_bytes(raw)
                from_addr = _decode_header(msg.get("From", "")).lower()
                subject = _decode_header(msg.get("Subject", ""))

                # Quick pre-filter: only process career-portal-like emails
                if not any(p in from_addr for p in CAREER_PORTAL_SENDERS):
                    continue

                # Fetch full body for classification
                status2, full_data = mail.fetch(msg_id, "(RFC822)")
                if status2 != "OK" or not full_data or not full_data[0]:
                    continue
                raw_full = full_data[0][1] if isinstance(full_data[0], tuple) else full_data[0]
                full_msg = email_lib.message_from_bytes(raw_full)
                body = _extract_body(full_msg)[:1000]

                classification = classify_inbox_email(subject, body, from_addr)

                if classification["type"] in ("rejection", "interview", "confirmation"):
                    # Try to match to an application
                    matched_app = _match_to_application(conn, from_addr, subject, body)

                    entry = {
                        "from": from_addr,
                        "subject": subject,
                        "type": classification["type"],
                        "confidence": classification["confidence"],
                        "body_preview": body[:200],
                        "matched_application": matched_app,
                    }
                    results.append(entry)

                    # Auto-update application status if matched
                    if matched_app and classification["confidence"] in ("high", "medium"):
                        app_id = matched_app["id"]
                        if classification["type"] == "rejection":
                            conn.execute("UPDATE applications SET status = 'rejected' WHERE id = ? AND status = 'applied'", (app_id,))
                            updated["rejections"] += 1
                        elif classification["type"] == "interview":
                            conn.execute("UPDATE applications SET status = 'interviewing' WHERE id = ? AND status = 'applied'", (app_id,))
                            updated["interviews"] += 1
                        elif classification["type"] == "confirmation":
                            updated["confirmations"] += 1

                        # Also update pipeline_leads if exists
                        if classification["type"] == "rejection":
                            conn.execute(
                                "UPDATE pipeline_leads SET stage = 'rejected', updated_at = datetime('now') WHERE post_id = ? AND stage = 'applied'",
                                (matched_app.get("post_id"),)
                            )
                        elif classification["type"] == "interview":
                            conn.execute(
                                "UPDATE pipeline_leads SET stage = 'interviewing', updated_at = datetime('now') WHERE post_id = ? AND stage IN ('applied', 'replied')",
                                (matched_app.get("post_id"),)
                            )

                        conn.commit()

            except Exception:
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
