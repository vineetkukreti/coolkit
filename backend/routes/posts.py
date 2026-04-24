"""Posts / DB query routes — list posts, stats, outreach-ready."""

import threading

from fastapi import APIRouter, HTTPException

from db import init_db, query_posts, get_stats, get_posts_for_outreach
from email_finder.enrich import find_emails_for_company

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
# Endpoints
# ───────────────────────────────────────────────

@router.get("/api/db/posts")
def api_get_posts(
    role: str = None,
    domain: str = None,
    has_email: bool = None,
    is_hiring: bool = None,
    company: str = None,
    limit: int = 200,
):
    conn = _get_db()
    posts = query_posts(
        conn, role=role, domain=domain, has_email=has_email,
        is_hiring=is_hiring, company=company, limit=limit,
    )
    return {"posts": posts, "total": len(posts)}


@router.get("/api/db/stats")
def api_get_db_stats():
    conn = _get_db()
    return get_stats(conn)


@router.get("/api/db/outreach-ready")
def api_outreach_ready():
    conn = _get_db()
    posts = get_posts_for_outreach(conn)
    # Attach any existing drafts/sent status from email_outreach
    for p in posts:
        draft = conn.execute(
            """SELECT id, subject, body, status, sent_at FROM email_outreach
               WHERE post_id = ? ORDER BY created_at DESC LIMIT 1""",
            (p["id"],),
        ).fetchone()
        if draft:
            d = dict(draft)
            p["draft_id"] = d["id"]
            p["draft_subject"] = d["subject"]
            p["draft_body"] = d["body"]
            p["email_status"] = d["status"]
            p["sent_at"] = d["sent_at"]
        p["source_type"] = "post"

    # ── Also include startup leads with emails that haven't been contacted ──
    # Exclude emails already sent via email_outreach
    sent_emails = set()
    for row in conn.execute("SELECT DISTINCT recipient_email FROM email_outreach WHERE status = 'sent'").fetchall():
        sent_emails.add(row[0].lower())

    leads = conn.execute(
        """SELECT id, company_name, email, description, industry, location,
                  website, linkedin_url, funding_info, tags
           FROM startup_leads
           WHERE email IS NOT NULL AND email != ''
             AND email_status = 'not_contacted'
           ORDER BY
             CASE WHEN website IS NOT NULL AND website != '' THEN 0 ELSE 1 END,
             company_name
        """
    ).fetchall()

    for lead in leads:
        lead = dict(lead)
        # Skip if any of this lead's emails were already sent
        lead_emails = [e.strip().lower() for e in lead["email"].split(",")]
        if any(e in sent_emails for e in lead_emails):
            continue

        # Format as a post-like object so the UI can handle it uniformly
        posts.append({
            "id": lead["id"],
            "author_name": lead["company_name"],
            "author_headline": lead.get("industry") or "Healthcare Startup",
            "author_profile": lead.get("linkedin_url") or "",
            "email": lead["email"],
            "content": lead.get("description") or "",
            "links": lead.get("website") or "",
            "domain_relevance": "High",
            "is_hiring": 0,
            "role": lead.get("tags") or "",
            "company": lead["company_name"],
            "location": lead.get("location") or "",
            "source_type": "startup_lead",
        })

    return {"posts": posts, "total": len(posts)}


@router.post("/api/db/posts/{post_id}/find-email")
def api_find_email_for_post(post_id: int):
    """Find emails for a single LinkedIn post by looking up its company."""
    conn = _get_db()

    row = conn.execute(
        """SELECT p.id, p.author_name, p.content, p.links,
                  (SELECT j.company FROM jobs j WHERE j.post_id = p.id LIMIT 1) as company,
                  (SELECT j.role FROM jobs j WHERE j.post_id = p.id LIMIT 1) as role,
                  (SELECT j.location FROM jobs j WHERE j.post_id = p.id LIMIT 1) as location
           FROM posts p WHERE p.id = ?""",
        (post_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")

    row = dict(row)
    company = row.get("company") or ""
    content = row.get("content") or ""
    author = row.get("author_name") or ""

    # Try to get company name from various sources
    if not company:
        if any(kw in author for kw in ["Ltd", "Pvt", "Inc", "LLC", "Corp", "Technologies", "Health", "Labs"]):
            company = author
        elif content:
            import re
            m = re.search(r'(?:at|@)\s+([A-Z][A-Za-z0-9\s&.]+?)(?:\s*[\n,\-|]|$)', content[:500])
            if m:
                company = m.group(1).strip()

    if not company:
        return {"status": "error", "post_id": post_id, "message": "Could not determine company name from post"}

    # Extract website from links
    website = ""
    raw_links = row.get("links") or ""
    if raw_links:
        for link in raw_links.split(","):
            link = link.strip()
            if link.startswith("http") and "linkedin.com" not in link and "lnkd.in" not in link:
                website = link
                break

    found = find_emails_for_company(company, website, row.get("location") or "")

    if found:
        best = ", ".join(f["email"] for f in found[:3])
        conn.execute("UPDATE posts SET email = ?, updated_at = datetime('now') WHERE id = ?", (best, post_id))
        if company:
            conn.execute(
                """UPDATE posts SET email = ?, updated_at = datetime('now')
                   WHERE id IN (
                       SELECT p.id FROM posts p JOIN jobs j ON j.post_id = p.id
                       WHERE j.company = ? AND (p.email IS NULL OR p.email = '')
                   )""",
                (best, company),
            )
        conn.commit()

    return {
        "status": "ok",
        "post_id": post_id,
        "company": company,
        "emails_found": len(found),
        "emails": [{"email": f["email"], "source": f["source"], "score": f["score"]} for f in found],
        "saved": ", ".join(f["email"] for f in found[:3]) if found else None,
    }
