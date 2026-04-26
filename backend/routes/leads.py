"""Startup leads routes — CRUD, stats, import, and email enrichment."""

import threading

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import init_db
from email_finder.enrich import find_emails_for_company, enrich_leads

router = APIRouter()

_local = threading.local()


def _get_db():
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = init_db()
    return _local.conn


# ───────────────────────────────────────────────
# Pydantic models
# ───────────────────────────────────────────────

class LeadUpdateRequest(BaseModel):
    email_status: str = ""
    email: str = ""
    notes: str = ""
    tags: str = ""


class EnrichRequest(BaseModel):
    max_leads: int = 50
    target: str = "startup_leads"  # "startup_leads" or "posts"


# ───────────────────────────────────────────────
# Enrichment state + worker
# ───────────────────────────────────────────────

enrichment_state = {
    "running": False,
    "current": 0,
    "total": 0,
    "current_company": "",
    "target": "",            # "startup_leads" or "posts"
    "results": [],           # last N progress events
    "summary": None,         # final {enriched, skipped, failed, total_emails_found}
}

_enrichment_lock = threading.Lock()


def _enrichment_worker(max_leads: int, target: str):
    """Background thread: find emails for leads without them."""
    enrichment_state["running"] = True
    enrichment_state["current"] = 0
    enrichment_state["total"] = 0
    enrichment_state["current_company"] = ""
    enrichment_state["target"] = target
    enrichment_state["results"] = []
    enrichment_state["summary"] = None

    conn = init_db()

    def on_progress(data):
        enrichment_state["results"].append(data)
        # Keep last 100
        if len(enrichment_state["results"]) > 100:
            enrichment_state["results"] = enrichment_state["results"][-100:]

        if data.get("type") in ("searching", "found", "not_found", "error"):
            enrichment_state["current"] = data.get("current", 0)
            enrichment_state["total"] = data.get("total", 0)
            enrichment_state["current_company"] = data.get("company", "")
        elif data.get("type") == "start":
            enrichment_state["total"] = data.get("total", 0)
        elif data.get("type") == "done":
            enrichment_state["summary"] = data

    try:
        enrich_leads(conn, max_leads=max_leads, target=target, on_progress=on_progress)
    except Exception as e:
        enrichment_state["results"].append({"type": "error", "error": str(e)[:300]})
    finally:
        enrichment_state["running"] = False
        conn.close()


# ───────────────────────────────────────────────
# Routes
# ───────────────────────────────────────────────

@router.get("/api/leads")
def api_get_leads(
    search: str = "",
    industry: str = "",
    country: str = "",
    email_status: str = "",
    has_email: bool = None,
    source: str = "",
    sort_by: str = "company_name",
    sort_dir: str = "asc",
    limit: int = 500,
    offset: int = 0,
):
    """List startup leads with filters, search, sorting, and pagination."""
    db_conn = _get_db()
    conditions = []
    params = []

    if search:
        conditions.append("(sl.company_name LIKE ? OR sl.description LIKE ? OR sl.email LIKE ? OR sl.tags LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s, s, s])
    if industry:
        conditions.append("sl.industry LIKE ?")
        params.append(f"%{industry}%")
    if country:
        conditions.append("sl.country = ?")
        params.append(country)
    if email_status:
        conditions.append("sl.email_status = ?")
        params.append(email_status)
    if has_email is True:
        conditions.append("sl.email IS NOT NULL AND sl.email != ''")
    if source:
        conditions.append("sl.source_file = ?")
        params.append(source)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Validate sort column
    valid_sorts = {"company_name", "industry", "location", "country", "email_status", "created_at", "funding_status"}
    sort_col = sort_by if sort_by in valid_sorts else "company_name"
    sort_direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

    # Total count
    total = db_conn.execute(f"SELECT COUNT(*) FROM startup_leads sl {where}", params).fetchone()[0]

    # Paginated results
    rows = db_conn.execute(
        f"""SELECT * FROM startup_leads sl {where}
            ORDER BY sl.{sort_col} {sort_direction}
            LIMIT ? OFFSET ?""",
        params + [limit, offset],
    ).fetchall()

    return {"leads": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/api/leads/stats")
def api_leads_stats():
    """Aggregate stats for startup leads dashboard."""
    db_conn = _get_db()
    total = db_conn.execute("SELECT COUNT(*) FROM startup_leads").fetchone()[0]
    with_email = db_conn.execute("SELECT COUNT(*) FROM startup_leads WHERE email IS NOT NULL AND email != ''").fetchone()[0]
    with_website = db_conn.execute("SELECT COUNT(*) FROM startup_leads WHERE website IS NOT NULL AND website != ''").fetchone()[0]
    with_linkedin = db_conn.execute("SELECT COUNT(*) FROM startup_leads WHERE linkedin_url IS NOT NULL AND linkedin_url != ''").fetchone()[0]

    by_country = {}
    for row in db_conn.execute("SELECT COALESCE(country, 'Unknown') as c, COUNT(*) as cnt FROM startup_leads GROUP BY c ORDER BY cnt DESC").fetchall():
        by_country[row["c"]] = row["cnt"]

    by_industry = {}
    for row in db_conn.execute("SELECT COALESCE(industry, 'Unknown') as ind, COUNT(*) as cnt FROM startup_leads GROUP BY ind ORDER BY cnt DESC").fetchall():
        by_industry[row["ind"]] = row["cnt"]

    by_source = {}
    for row in db_conn.execute("SELECT source_file, COUNT(*) as cnt FROM startup_leads GROUP BY source_file ORDER BY cnt DESC").fetchall():
        by_source[row["source_file"]] = row["cnt"]

    by_email_status = {}
    for row in db_conn.execute("SELECT email_status, COUNT(*) as cnt FROM startup_leads GROUP BY email_status ORDER BY cnt DESC").fetchall():
        by_email_status[row["email_status"]] = row["cnt"]

    by_funding = {}
    for row in db_conn.execute("SELECT COALESCE(funding_status, 'Unknown') as fs, COUNT(*) as cnt FROM startup_leads GROUP BY fs ORDER BY cnt DESC").fetchall():
        by_funding[row["fs"]] = row["cnt"]

    return {
        "total": total,
        "with_email": with_email,
        "with_website": with_website,
        "with_linkedin": with_linkedin,
        "by_country": by_country,
        "by_industry": by_industry,
        "by_source": by_source,
        "by_email_status": by_email_status,
        "by_funding": by_funding,
    }


@router.get("/api/leads/sources")
def api_leads_sources():
    """Get distinct source files for filter dropdown."""
    db_conn = _get_db()
    rows = db_conn.execute("SELECT DISTINCT source_file FROM startup_leads ORDER BY source_file").fetchall()
    return {"sources": [r["source_file"] for r in rows]}


@router.get("/api/leads/{lead_id}")
def api_get_lead(lead_id: int):
    """Get single lead details."""
    db_conn = _get_db()
    row = db_conn.execute("SELECT * FROM startup_leads WHERE id = ?", (lead_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    return dict(row)


@router.post("/api/leads/{lead_id}/update")
def api_update_lead(lead_id: int, req: LeadUpdateRequest):
    """Update a lead's email_status, email, notes, or tags."""
    db_conn = _get_db()
    ALLOWED_COLUMNS = {'email', 'notes', 'tags', 'status', 'email_status', 'company_name', 'website', 'linkedin_url', 'description'}
    updates = []
    params = []
    update_data = req.dict(exclude_unset=False)
    for col, val in update_data.items():
        if col in ALLOWED_COLUMNS and val:
            updates.append(f"{col} = ?")
            params.append(val)

    if not updates:
        return {"status": "ok", "message": "Nothing to update"}

    updates.append("updated_at = datetime('now')")
    params.append(lead_id)

    db_conn.execute(f"UPDATE startup_leads SET {', '.join(updates)} WHERE id = ?", params)
    db_conn.commit()
    return {"status": "ok", "message": "Lead updated"}


@router.post("/api/leads/import")
def api_import_leads():
    """Run lead import from files."""
    db_conn = _get_db()
    from services.import_leads import import_all as _import_all
    try:
        _import_all()
        total = db_conn.execute("SELECT COUNT(*) FROM startup_leads").fetchone()[0]
        return {"status": "ok", "message": f"Import complete. {total} total leads in database."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:300])


# ───────────────────────────────────────────────
# Enrichment routes
# ───────────────────────────────────────────────

@router.post("/api/leads/enrich/start")
def api_start_enrichment(req: EnrichRequest):
    """Start bulk email finding in background."""
    if enrichment_state["running"]:
        raise HTTPException(status_code=400, detail="Email finder already running. Wait or stop it first.")

    db_conn = _get_db()
    target = req.target if req.target in ("startup_leads", "posts") else "startup_leads"

    # Count how many need emails
    if target == "startup_leads":
        missing = db_conn.execute(
            "SELECT COUNT(*) FROM startup_leads WHERE email IS NULL OR email = ''"
        ).fetchone()[0]
    else:
        missing = db_conn.execute(
            """SELECT COUNT(DISTINCT j.company) FROM posts p
               LEFT JOIN jobs j ON j.post_id = p.id
               WHERE (p.email IS NULL OR p.email = '') AND p.is_hiring = 1
                 AND j.company IS NOT NULL AND j.company != ''"""
        ).fetchone()[0]

    if missing == 0:
        return {"status": "ok", "message": "All leads already have emails!"}

    actual = min(req.max_leads, missing)
    threading.Thread(target=_enrichment_worker, args=(actual, target), daemon=True).start()
    return {
        "status": "started",
        "message": f"Finding emails for {actual} {target.replace('_', ' ')} (out of {missing} without emails)...",
        "missing": missing,
        "processing": actual,
    }


@router.get("/api/leads/enrich/status")
def api_enrichment_status():
    """Poll this for enrichment progress."""
    found_count = sum(1 for r in enrichment_state["results"] if r.get("type") == "found")
    not_found = sum(1 for r in enrichment_state["results"] if r.get("type") == "not_found")
    errors = sum(1 for r in enrichment_state["results"] if r.get("type") == "error")

    return {
        "running": enrichment_state["running"],
        "current": enrichment_state["current"],
        "total": enrichment_state["total"],
        "current_company": enrichment_state["current_company"],
        "target": enrichment_state["target"],
        "found": found_count,
        "not_found": not_found,
        "errors": errors,
        "summary": enrichment_state["summary"],
        "results": enrichment_state["results"][-30:],  # last 30 for UI
    }


@router.post("/api/leads/enrich/stop")
def api_stop_enrichment():
    """Stop the running enrichment."""
    enrichment_state["running"] = False
    return {"status": "stopped"}


@router.post("/api/leads/enrich/single/{lead_id}")
def api_enrich_single(lead_id: int):
    """Find emails for a single lead (synchronous)."""
    db_conn = _get_db()

    row = db_conn.execute(
        "SELECT id, company_name, website, location FROM startup_leads WHERE id = ?",
        (lead_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")

    row = dict(row)
    found = find_emails_for_company(row["company_name"], row.get("website", ""), row.get("location", ""))

    if found:
        best = ", ".join(f["email"] for f in found[:3])
        db_conn.execute(
            "UPDATE startup_leads SET email = ?, updated_at = datetime('now') WHERE id = ?",
            (best, lead_id),
        )
        db_conn.commit()

    return {
        "status": "ok",
        "lead_id": lead_id,
        "company": row["company_name"],
        "emails_found": len(found),
        "emails": [{"email": f["email"], "source": f["source"], "score": f["score"]} for f in found],
        "saved": ", ".join(f["email"] for f in found[:3]) if found else None,
    }
