"""
Referral Detector — Check for LinkedIn connections before cold applying.

Referrals have 10x the conversion rate of cold applications. Before
auto-applying, check if we've previously scraped posts from people at
the target company, or if we have email contacts there.

This uses LOCAL data (already scraped posts and leads) — no external
API calls needed. Checks:
1. Authors of scraped posts who work at the company
2. Pipeline leads at the company
3. Email outreach contacts at the company
4. Startup leads database

Usage:
    from services.referral_detector import find_connections, has_connections

    connections = find_connections(conn, "Hippocratic AI")
    if connections["has_connections"]:
        # Reach out for referral instead of cold applying
        for contact in connections["contacts"]:
            print(f"  {contact['name']} — {contact['source']}")
"""

import sqlite3


def find_connections(conn: sqlite3.Connection, company: str) -> dict:
    """Find any existing connections or contacts at a company.

    Searches local DB for people we've interacted with at this company.

    Returns:
        {
            "has_connections": bool,
            "company": str,
            "contacts": [{"name": str, "email": str, "source": str, "detail": str}],
            "recommendation": str,  # "referral" | "warm_intro" | "cold_apply"
        }
    """
    if not company or len(company.strip()) < 2:
        return {"has_connections": False, "company": company, "contacts": [], "recommendation": "cold_apply"}

    company_lower = company.lower().strip()
    contacts = []

    # 1. Check post authors who work at this company
    try:
        rows = conn.execute("""
            SELECT DISTINCT p.author_name, p.author_profile, p.author_headline, p.email
            FROM posts p
            WHERE LOWER(p.author_headline) LIKE ? OR LOWER(p.content) LIKE ?
            AND p.author_name IS NOT NULL AND p.author_name != ''
            LIMIT 10
        """, (f"%{company_lower}%", f"%{company_lower}%hiring%")).fetchall()

        for row in rows:
            r = dict(row) if hasattr(row, 'keys') else {
                "author_name": row[0], "author_profile": row[1],
                "author_headline": row[2], "email": row[3],
            }
            name = r.get("author_name", "")
            if name and company_lower in (r.get("author_headline", "") or "").lower():
                contacts.append({
                    "name": name,
                    "email": r.get("email", ""),
                    "profile": r.get("author_profile", ""),
                    "headline": r.get("author_headline", ""),
                    "source": "scraped_post",
                    "detail": f"Posted about hiring at {company}",
                })
    except Exception:
        pass

    # 2. Check pipeline leads at this company
    try:
        rows = conn.execute("""
            SELECT recipient_name, recipient_email, role, stage
            FROM pipeline_leads
            WHERE LOWER(company) LIKE ?
            LIMIT 10
        """, (f"%{company_lower}%",)).fetchall()

        for row in rows:
            r = dict(row) if hasattr(row, 'keys') else {
                "recipient_name": row[0], "recipient_email": row[1],
                "role": row[2], "stage": row[3],
            }
            contacts.append({
                "name": r.get("recipient_name", ""),
                "email": r.get("recipient_email", ""),
                "profile": "",
                "headline": r.get("role", ""),
                "source": "pipeline_lead",
                "detail": f"Pipeline stage: {r.get('stage', 'unknown')}",
            })
    except Exception:
        pass

    # 3. Check email outreach history (people we've already emailed)
    try:
        rows = conn.execute("""
            SELECT eo.recipient_email, eo.subject, eo.status, p.author_name
            FROM email_outreach eo
            LEFT JOIN posts p ON eo.post_id = p.id
            LEFT JOIN jobs j ON j.post_id = p.id
            WHERE LOWER(j.company) LIKE ? OR LOWER(eo.subject) LIKE ?
            LIMIT 10
        """, (f"%{company_lower}%", f"%{company_lower}%")).fetchall()

        for row in rows:
            r = dict(row) if hasattr(row, 'keys') else {
                "recipient_email": row[0], "subject": row[1],
                "status": row[2], "author_name": row[3],
            }
            # Avoid duplicates
            email = r.get("recipient_email", "")
            if email and not any(c["email"] == email for c in contacts):
                contacts.append({
                    "name": r.get("author_name", ""),
                    "email": email,
                    "profile": "",
                    "headline": "",
                    "source": "email_outreach",
                    "detail": f"Previously emailed (status: {r.get('status', '?')})",
                })
    except Exception:
        pass

    # 4. Check startup leads database
    try:
        rows = conn.execute("""
            SELECT company_name, email, linkedin_url, website
            FROM startup_leads
            WHERE LOWER(company_name) LIKE ?
            LIMIT 5
        """, (f"%{company_lower}%",)).fetchall()

        for row in rows:
            r = dict(row) if hasattr(row, 'keys') else {
                "company_name": row[0], "email": row[1],
                "linkedin_url": row[2], "website": row[3],
            }
            email = r.get("email", "")
            if email and not any(c["email"] == email for c in contacts):
                contacts.append({
                    "name": r.get("company_name", ""),
                    "email": email,
                    "profile": r.get("linkedin_url", ""),
                    "headline": "",
                    "source": "startup_leads",
                    "detail": f"Company lead — {r.get('website', '')}",
                })
    except Exception:
        pass

    # Deduplicate by email
    seen_emails = set()
    unique_contacts = []
    for c in contacts:
        email = c.get("email", "").lower()
        if email and email in seen_emails:
            continue
        if email:
            seen_emails.add(email)
        unique_contacts.append(c)

    has_connections = len(unique_contacts) > 0

    # Recommendation
    if has_connections:
        # Check if we've already had positive interaction
        has_replied = any(c.get("detail", "").find("replied") >= 0 for c in unique_contacts)
        has_pipeline = any(c["source"] == "pipeline_lead" for c in unique_contacts)

        if has_replied:
            recommendation = "warm_followup"
        elif has_pipeline:
            recommendation = "warm_intro"
        else:
            recommendation = "referral_outreach"
    else:
        recommendation = "cold_apply"

    return {
        "has_connections": has_connections,
        "company": company,
        "contacts": unique_contacts,
        "total_contacts": len(unique_contacts),
        "recommendation": recommendation,
    }


def has_connections(conn: sqlite3.Connection, company: str) -> bool:
    """Quick check if we have any connections at a company."""
    result = find_connections(conn, company)
    return result["has_connections"]
