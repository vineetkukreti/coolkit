"""Pipeline tracker routes — manage leads through application stages."""

import re
import threading

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import init_db

router = APIRouter()

# ───────────────────────────────────────────────
# Thread-local DB connection
# ───────────────────────────────────────────────
_local = threading.local()


def _get_db():
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = init_db()
    return _local.conn


# ───────────────────────────────────────────────
# Pipeline stages
# ───────────────────────────────────────────────

PIPELINE_STAGES = ["applied", "replied", "interviewing", "offer", "rejected"]


# ───────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────

def _name_from_email(email_addr: str) -> str:
    """Extract a human-readable name from an email address prefix."""
    if not email_addr:
        return ""
    prefix = email_addr.split("@")[0]
    # If the prefix IS a generic role (hr, info, careers, etc.), use domain as name instead
    generic_prefixes = {"hr", "info", "careers", "talent", "hiring", "jobs", "recruit",
                        "admin", "contact", "team", "hello", "support", "office"}
    clean = re.sub(r'[._\-\d]+', '', prefix).lower()
    if clean in generic_prefixes:
        # Use domain name instead
        domain = email_addr.split("@")[1].split(".")[0] if "@" in email_addr else ""
        return domain.title() + " Team" if domain else prefix.title()
    # Split on dots, underscores, hyphens and capitalize
    parts = re.split(r'[._\-]+', prefix)
    # Strip trailing digits from name parts (ssingh1 -> ssingh)
    parts = [re.sub(r'\d+$', '', p) for p in parts]
    name = " ".join(p.capitalize() for p in parts if p)
    return name if name else email_addr.split("@")[0]


def _role_from_subject(subject: str) -> str:
    """Extract role/position from email subject line."""
    if not subject:
        return ""
    # Subjects are typically: "Role Title | Your Skills Match" or "Role Title — Why I'm a fit"
    # Take everything before the first separator
    for sep in [" | ", " — ", " - ", " – "]:
        if sep in subject:
            return subject.split(sep)[0].strip()
    return subject.strip()[:60]


def _company_from_email(email_addr: str) -> str:
    """Extract company name from email domain."""
    if not email_addr or "@" not in email_addr:
        return ""
    domain = email_addr.split("@")[1].lower()
    # Skip generic email providers
    generic = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "protonmail.com",
               "icloud.com", "mail.com", "aol.com", "yandex.com", "zoho.com"]
    if domain in generic:
        return ""
    # Remove TLD and capitalize
    company = domain.split(".")[0]
    # Clean up and capitalize
    company = re.sub(r'[_-]+', ' ', company)
    return company.title()


# ───────────────────────────────────────────────
# Pydantic models
# ───────────────────────────────────────────────

class PipelineUpdateStage(BaseModel):
    lead_id: int
    stage: str


class PipelineAddNote(BaseModel):
    lead_id: int
    content: str


# ───────────────────────────────────────────────
# Endpoints
# ───────────────────────────────────────────────

@router.get("/api/pipeline")
def api_pipeline_list():
    """Get all pipeline leads with their latest info."""
    db_conn = _get_db()
    rows = db_conn.execute(
        """SELECT pl.id, pl.post_id, pl.outreach_id, pl.recipient_name, pl.recipient_email,
                  pl.role, pl.company, pl.location, pl.stage, pl.source, pl.created_at, pl.updated_at,
                  eo.reply_type, eo.reply_preview, eo.reply_detected_at, eo.subject as email_subject,
                  p.content as post_content, p.links as post_links, p.post_url,
                  p.author_headline, p.domain_relevance
           FROM pipeline_leads pl
           LEFT JOIN email_outreach eo ON eo.id = pl.outreach_id
           LEFT JOIN posts p ON p.id = pl.post_id
           ORDER BY pl.updated_at DESC"""
    ).fetchall()

    leads = []
    for r in rows:
        lead = dict(r)
        # Enrich missing fields from email data
        if not lead.get("recipient_name"):
            lead["recipient_name"] = _name_from_email(lead.get("recipient_email", ""))
        if not lead.get("role"):
            lead["role"] = _role_from_subject(lead.get("email_subject", ""))
        if not lead.get("company"):
            lead["company"] = _company_from_email(lead.get("recipient_email", ""))
        leads.append(lead)

    return {"leads": leads, "total": len(leads)}


@router.get("/api/pipeline/stats")
def api_pipeline_stats():
    """Pipeline stage counts."""
    db_conn = _get_db()
    counts = {}
    for stage in PIPELINE_STAGES:
        counts[stage] = db_conn.execute(
            "SELECT COUNT(*) FROM pipeline_leads WHERE stage = ?", (stage,)
        ).fetchone()[0]
    counts["total"] = sum(counts.values())

    # Also return reply type breakdown for replied leads
    reply_types = {}
    for row in db_conn.execute(
        """SELECT eo.reply_type, COUNT(*) as c
           FROM pipeline_leads pl
           JOIN email_outreach eo ON eo.id = pl.outreach_id
           WHERE eo.reply_type IS NOT NULL
           GROUP BY eo.reply_type"""
    ).fetchall():
        reply_types[row[0]] = row[1]
    counts["reply_types"] = reply_types

    return counts


@router.get("/api/pipeline/lead/{lead_id}")
def api_pipeline_lead(lead_id: int):
    """Get full lead detail with events, notes, and email history."""
    db_conn = _get_db()
    lead = db_conn.execute(
        """SELECT pl.*, p.content as post_content, p.links as post_links, p.post_url,
                  p.author_headline, p.domain_relevance, p.email as post_email,
                  eo.reply_type, eo.reply_preview, eo.reply_detected_at, eo.subject as email_subject,
                  eo.body as email_body, eo.status as email_status
           FROM pipeline_leads pl
           LEFT JOIN posts p ON p.id = pl.post_id
           LEFT JOIN email_outreach eo ON eo.id = pl.outreach_id
           WHERE pl.id = ?""",
        (lead_id,),
    ).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead = dict(lead)

    # Enrich missing fields
    if not lead.get("recipient_name"):
        lead["recipient_name"] = _name_from_email(lead.get("recipient_email", ""))
    if not lead.get("role"):
        lead["role"] = _role_from_subject(lead.get("email_subject", ""))
    if not lead.get("company"):
        lead["company"] = _company_from_email(lead.get("recipient_email", ""))

    # Events (timeline)
    events = db_conn.execute(
        "SELECT * FROM pipeline_events WHERE lead_id = ? ORDER BY created_at ASC", (lead_id,)
    ).fetchall()
    lead["events"] = [dict(e) for e in events]

    # Notes
    notes = db_conn.execute(
        "SELECT * FROM pipeline_notes WHERE lead_id = ? ORDER BY created_at DESC", (lead_id,)
    ).fetchall()
    lead["notes"] = [dict(n) for n in notes]

    # Email outreach history — use outreach_id (always available), fall back to post_id
    if lead.get("outreach_id"):
        emails = db_conn.execute(
            "SELECT * FROM email_outreach WHERE id = ? OR post_id = ? ORDER BY created_at ASC",
            (lead["outreach_id"], lead.get("post_id") or -1)
        ).fetchall()
    elif lead.get("post_id"):
        emails = db_conn.execute(
            "SELECT * FROM email_outreach WHERE post_id = ? ORDER BY created_at ASC", (lead["post_id"],)
        ).fetchall()
    else:
        emails = []
    lead["emails"] = [dict(e) for e in emails]

    return lead


@router.post("/api/pipeline/update-stage")
def api_pipeline_update_stage(req: PipelineUpdateStage):
    """Move a lead to a different stage."""
    db_conn = _get_db()
    if req.stage not in PIPELINE_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {PIPELINE_STAGES}")

    old = db_conn.execute("SELECT stage FROM pipeline_leads WHERE id = ?", (req.lead_id,)).fetchone()
    if not old:
        raise HTTPException(status_code=404, detail="Lead not found")

    old_stage = old["stage"]
    db_conn.execute(
        "UPDATE pipeline_leads SET stage = ?, updated_at = datetime('now') WHERE id = ?",
        (req.stage, req.lead_id),
    )
    # Log event
    db_conn.execute(
        "INSERT INTO pipeline_events (lead_id, event_type, title, content) VALUES (?, 'stage_change', ?, ?)",
        (req.lead_id, f"Status \u2192 {req.stage.title()}", f"Moved from {old_stage} to {req.stage}"),
    )
    db_conn.commit()
    return {"status": "ok", "message": f"Lead moved to {req.stage}"}


@router.post("/api/pipeline/add-note")
def api_pipeline_add_note(req: PipelineAddNote):
    """Add a note to a lead."""
    db_conn = _get_db()
    db_conn.execute(
        "INSERT INTO pipeline_notes (lead_id, content) VALUES (?, ?)",
        (req.lead_id, req.content),
    )
    db_conn.execute(
        "INSERT INTO pipeline_events (lead_id, event_type, title, content) VALUES (?, 'note', 'Note Added', ?)",
        (req.lead_id, req.content),
    )
    db_conn.execute("UPDATE pipeline_leads SET updated_at = datetime('now') WHERE id = ?", (req.lead_id,))
    db_conn.commit()
    return {"status": "ok"}


@router.post("/api/pipeline/sync")
def api_pipeline_sync():
    """Sync sent AND replied emails into pipeline_leads, and update stale stages."""
    db_conn = _get_db()
    inserted = 0
    updated = 0

    # 1. Import sent + replied emails not yet in pipeline
    untracked = db_conn.execute(
        """SELECT eo.id, eo.post_id, eo.recipient_email, eo.subject, eo.body, eo.sent_at,
                  eo.status as email_status, eo.reply_type, eo.reply_preview,
                  p.author_name,
                  (SELECT j.role FROM jobs j WHERE j.post_id = eo.post_id LIMIT 1) as role,
                  (SELECT j2.company FROM jobs j2 WHERE j2.post_id = eo.post_id LIMIT 1) as company,
                  (SELECT j3.location FROM jobs j3 WHERE j3.post_id = eo.post_id LIMIT 1) as location
           FROM email_outreach eo
           LEFT JOIN posts p ON p.id = eo.post_id
           WHERE eo.status IN ('sent', 'replied')
             AND eo.id NOT IN (SELECT outreach_id FROM pipeline_leads WHERE outreach_id IS NOT NULL)"""
    ).fetchall()

    for row in untracked:
        row = dict(row)
        # Determine initial stage based on email status
        if row.get("email_status") == "replied":
            if row.get("reply_type") == "rejection":
                stage = "rejected"
            elif row.get("reply_type") == "auto_reply":
                stage = "applied"
            else:
                stage = "replied"
        else:
            stage = "applied"

        # Derive name/role/company from email data when post join fails
        name = row.get("author_name", "")
        if not name:
            name = _name_from_email(row.get("recipient_email", ""))
        role = row.get("role", "")
        if not role:
            role = _role_from_subject(row.get("subject", ""))
        company = row.get("company", "")
        if not company:
            company = _company_from_email(row.get("recipient_email", ""))

        db_conn.execute(
            """INSERT INTO pipeline_leads (post_id, outreach_id, recipient_name, recipient_email, role, company, location, stage, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'email', ?)""",
            (row.get("post_id"), row["id"], name, row["recipient_email"],
             role, company, row.get("location", ""),
             stage, row.get("sent_at") or ""),
        )
        lead_id = db_conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Create initial timeline event
        db_conn.execute(
            "INSERT INTO pipeline_events (lead_id, event_type, title, content, created_at) VALUES (?, 'email_sent', 'Email Sent', ?, ?)",
            (lead_id, f"Subject: {row.get('subject', '')}", row.get("sent_at") or ""),
        )

        # If already replied, add reply event too
        if row.get("email_status") == "replied" and row.get("reply_type"):
            db_conn.execute(
                "INSERT INTO pipeline_events (lead_id, event_type, title, content) VALUES (?, 'email_reply', ?, ?)",
                (lead_id, f"Reply Detected ({row['reply_type']})",
                 f"[{row['reply_type'].upper()}] {(row.get('reply_preview') or '')[:150]}"),
            )

        inserted += 1

    # 2. Sync stale pipeline stages — update leads where email_outreach has newer status
    stale = db_conn.execute(
        """SELECT pl.id, pl.stage, eo.status as email_status, eo.reply_type
           FROM pipeline_leads pl
           JOIN email_outreach eo ON eo.id = pl.outreach_id
           WHERE eo.status = 'replied'
             AND pl.stage = 'applied'
             AND eo.reply_type IS NOT NULL
             AND eo.reply_type != 'auto_reply'"""
    ).fetchall()

    for row in stale:
        new_stage = "rejected" if row["reply_type"] == "rejection" else "replied"
        db_conn.execute(
            "UPDATE pipeline_leads SET stage = ?, updated_at = datetime('now') WHERE id = ?",
            (new_stage, row["id"])
        )
        db_conn.execute(
            "INSERT INTO pipeline_events (lead_id, event_type, title, content) VALUES (?, 'stage_change', ?, ?)",
            (row["id"], f"Auto-synced \u2192 {new_stage.title()}",
             f"Email reply detected as {row['reply_type']}"),
        )
        updated += 1

    # 3. Backfill empty role/company/name on existing leads
    enriched = 0
    empty_leads = db_conn.execute(
        """SELECT pl.id, pl.recipient_email, eo.subject
           FROM pipeline_leads pl
           LEFT JOIN email_outreach eo ON eo.id = pl.outreach_id
           WHERE (pl.role IS NULL OR pl.role = '' OR pl.company IS NULL OR pl.company = ''
                  OR pl.recipient_name IS NULL OR pl.recipient_name = '')"""
    ).fetchall()

    for row in empty_leads:
        updates = {}
        current = db_conn.execute(
            "SELECT recipient_name, role, company FROM pipeline_leads WHERE id = ?", (row["id"],)
        ).fetchone()
        if not current["recipient_name"]:
            updates["recipient_name"] = _name_from_email(row["recipient_email"])
        if not current["role"]:
            updates["role"] = _role_from_subject(row["subject"])
        if not current["company"]:
            updates["company"] = _company_from_email(row["recipient_email"])
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            db_conn.execute(
                f"UPDATE pipeline_leads SET {set_clause} WHERE id = ?",
                (*updates.values(), row["id"])
            )
            enriched += 1

    db_conn.commit()
    return {
        "status": "ok",
        "synced": inserted,
        "stages_updated": updated,
        "enriched": enriched,
        "message": f"Synced {inserted} new leads, updated {updated} stages, enriched {enriched} records"
    }


@router.get("/api/pipeline/funnel")
def api_pipeline_funnel():
    """Job search funnel analytics — conversion rates between stages."""
    db_conn = _get_db()

    # Stage counts
    stages = {}
    for stage in ["applied", "replied", "interviewing", "offer", "rejected"]:
        stages[stage] = db_conn.execute(
            "SELECT COUNT(*) FROM pipeline_leads WHERE stage = ?", (stage,)
        ).fetchone()[0]

    total = sum(stages.values())

    # Funnel conversion rates
    funnel = []
    stage_order = ["applied", "replied", "interviewing", "offer"]
    for i, stage in enumerate(stage_order):
        # For "applied", also count everything that progressed past it
        if stage == "applied":
            count_at_or_past = total  # Everyone starts at applied
        else:
            count_at_or_past = sum(stages.get(s, 0) for s in stage_order[i:])

        rate = round((count_at_or_past / max(total, 1)) * 100, 1)
        funnel.append({
            "stage": stage,
            "label": stage.title(),
            "count": count_at_or_past,
            "total": total,
            "conversion_rate": rate,
            "drop_off": round(100 - rate, 1),
        })

    # Time-to-stage analytics
    avg_times = {}
    for stage in ["replied", "interviewing", "offer", "rejected"]:
        row = db_conn.execute(
            """SELECT AVG(JULIANDAY(pl.updated_at) - JULIANDAY(pl.created_at)) as avg_days
               FROM pipeline_leads pl WHERE pl.stage = ? AND pl.updated_at IS NOT NULL AND pl.created_at IS NOT NULL""",
            (stage,)
        ).fetchone()
        avg_days = row[0] if row and row[0] else None
        if avg_days is not None:
            avg_times[stage] = round(avg_days, 1)

    # Application method breakdown
    methods = []
    for row in db_conn.execute(
        """SELECT apply_method, COUNT(*) as total,
                  SUM(CASE WHEN status = 'applied' THEN 1 ELSE 0 END) as applied,
                  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                  SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped
           FROM applications GROUP BY apply_method"""
    ).fetchall():
        methods.append({
            "method": row["apply_method"] or "unknown",
            "total": row["total"],
            "applied": row["applied"],
            "failed": row["failed"],
            "success_rate": round((row["applied"] / max(row["total"], 1)) * 100, 1),
        })

    # Weekly activity
    weekly = []
    for row in db_conn.execute(
        """SELECT DATE(applied_at) as day, COUNT(*) as count
           FROM applications
           WHERE applied_at >= datetime('now', '-30 days')
           GROUP BY day ORDER BY day"""
    ).fetchall():
        weekly.append({"date": row["day"], "count": row["count"]})

    # Source effectiveness (which sources lead to replies)
    sources = []
    for row in db_conn.execute(
        """SELECT pl.source, COUNT(*) as total,
                  SUM(CASE WHEN pl.stage IN ('replied', 'interviewing', 'offer') THEN 1 ELSE 0 END) as responded
           FROM pipeline_leads pl
           GROUP BY pl.source"""
    ).fetchall():
        sources.append({
            "source": row["source"] or "unknown",
            "total": row["total"],
            "responded": row["responded"],
            "response_rate": round((row["responded"] / max(row["total"], 1)) * 100, 1),
        })

    return {
        "funnel": funnel,
        "stages": stages,
        "total": total,
        "rejected": stages.get("rejected", 0),
        "rejection_rate": round((stages.get("rejected", 0) / max(total, 1)) * 100, 1),
        "avg_time_to_stage": avg_times,
        "methods": methods,
        "weekly_activity": weekly,
        "source_effectiveness": sources,
    }
