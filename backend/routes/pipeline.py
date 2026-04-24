"""Pipeline tracker routes — manage leads through application stages."""

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
                  p.content as post_content, p.links as post_links, p.post_url,
                  p.author_headline, p.domain_relevance
           FROM pipeline_leads pl
           LEFT JOIN posts p ON p.id = pl.post_id
           ORDER BY pl.updated_at DESC"""
    ).fetchall()
    return {"leads": [dict(r) for r in rows], "total": len(rows)}


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
    return counts


@router.get("/api/pipeline/lead/{lead_id}")
def api_pipeline_lead(lead_id: int):
    """Get full lead detail with events, notes, and email history."""
    db_conn = _get_db()
    lead = db_conn.execute(
        """SELECT pl.*, p.content as post_content, p.links as post_links, p.post_url,
                  p.author_headline, p.domain_relevance, p.email as post_email
           FROM pipeline_leads pl
           LEFT JOIN posts p ON p.id = pl.post_id
           WHERE pl.id = ?""",
        (lead_id,),
    ).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead = dict(lead)

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

    # Email outreach history for this post
    if lead.get("post_id"):
        emails = db_conn.execute(
            "SELECT * FROM email_outreach WHERE post_id = ? ORDER BY created_at ASC", (lead["post_id"],)
        ).fetchall()
        lead["emails"] = [dict(e) for e in emails]
    else:
        lead["emails"] = []

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
    """Sync sent emails into pipeline_leads (auto-create leads for sent emails not yet tracked)."""
    db_conn = _get_db()
    inserted = 0
    sent = db_conn.execute(
        """SELECT eo.id, eo.post_id, eo.recipient_email, eo.subject, eo.body, eo.sent_at,
                  p.author_name,
                  (SELECT j.role FROM jobs j WHERE j.post_id = eo.post_id LIMIT 1) as role,
                  (SELECT j2.company FROM jobs j2 WHERE j2.post_id = eo.post_id LIMIT 1) as company,
                  (SELECT j3.location FROM jobs j3 WHERE j3.post_id = eo.post_id LIMIT 1) as location
           FROM email_outreach eo
           LEFT JOIN posts p ON p.id = eo.post_id
           WHERE eo.status = 'sent'
             AND eo.id NOT IN (SELECT outreach_id FROM pipeline_leads WHERE outreach_id IS NOT NULL)"""
    ).fetchall()

    for row in sent:
        row = dict(row)
        db_conn.execute(
            """INSERT INTO pipeline_leads (post_id, outreach_id, recipient_name, recipient_email, role, company, location, stage, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'applied', 'email', ?)""",
            (row.get("post_id"), row["id"], row.get("author_name", ""), row["recipient_email"],
             row.get("role", ""), row.get("company", ""), row.get("location", ""),
             row.get("sent_at") or ""),
        )
        lead_id = db_conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # Create initial timeline event
        db_conn.execute(
            "INSERT INTO pipeline_events (lead_id, event_type, title, content, created_at) VALUES (?, 'email_sent', 'Email Sent', ?, ?)",
            (lead_id, f"Subject: {row.get('subject', '')}", row.get("sent_at") or ""),
        )
        inserted += 1

    db_conn.commit()
    return {"status": "ok", "synced": inserted, "message": f"Synced {inserted} new leads into pipeline"}
