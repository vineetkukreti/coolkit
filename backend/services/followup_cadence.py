"""
followup_cadence.py — Follow-up Cadence Tracker for linkedin-job-parser.

Python port of career-ops/followup-cadence.mjs adapted for our SQLite schema.
Computes follow-up urgency for sent outreach emails and determines next
follow-up dates based on configurable cadence rules.

Usage:
    from followup_cadence import analyze_followups, record_followup
    from db import init_db

    conn = init_db()
    report = analyze_followups(conn)
    # report["entries"] — list of outreach items with urgency
    # report["metadata"] — summary counts

    record_followup(conn, outreach_id=42)
    conn.close()
"""

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path("data/linkedin_jobs.db")

# ---------------------------------------------------------------------------
# Cadence configuration (days)
# ---------------------------------------------------------------------------

CADENCE = {
    "applied_first": 7,          # days before first follow-up
    "applied_subsequent": 7,     # days between follow-ups
    "applied_max_followups": 2,  # max follow-ups before cold
    "responded_initial": 1,      # days after response to follow up
    "responded_subsequent": 3,   # days between response follow-ups
    "interview_thankyou": 1,     # days to send thank-you
}

ACTIONABLE_STAGES = {"applied", "responded", "interview"}

# ---------------------------------------------------------------------------
# Urgency logic
# ---------------------------------------------------------------------------


def compute_urgency(
    stage: str,
    days_since_sent: int,
    days_since_last_followup: int | None,
    followup_count: int,
) -> str:
    """Determine urgency level for an outreach entry.

    Returns one of: "urgent", "overdue", "waiting", "cold".
    """
    if stage == "applied":
        if followup_count >= CADENCE["applied_max_followups"]:
            return "cold"
        if followup_count == 0 and days_since_sent >= CADENCE["applied_first"]:
            return "overdue"
        if (
            followup_count > 0
            and days_since_last_followup is not None
            and days_since_last_followup >= CADENCE["applied_subsequent"]
        ):
            return "overdue"
        return "waiting"

    if stage == "responded":
        if days_since_sent < CADENCE["responded_initial"]:
            return "urgent"
        if days_since_sent >= CADENCE["responded_subsequent"]:
            return "overdue"
        return "waiting"

    if stage == "interview":
        if days_since_sent >= CADENCE["interview_thankyou"]:
            return "overdue"
        return "waiting"

    return "waiting"


# ---------------------------------------------------------------------------
# Next follow-up date
# ---------------------------------------------------------------------------


def _add_days(d: date, n: int) -> str:
    """Return ISO date string for *d + n days*."""
    return (d + timedelta(days=n)).isoformat()


def _parse_date(s: str | None) -> date | None:
    """Parse an ISO-format date string (YYYY-MM-DD or datetime)."""
    if not s:
        return None
    try:
        # Handle both "2026-04-10" and "2026-04-10 14:30:00"
        return datetime.fromisoformat(s).date()
    except (ValueError, TypeError):
        return None


def compute_next_followup_date(
    stage: str,
    sent_date: str | None,
    last_followup_date: str | None,
    followup_count: int,
) -> str | None:
    """Compute the next follow-up date as an ISO string, or None if cold."""
    sent_d = _parse_date(sent_date)
    last_d = _parse_date(last_followup_date)

    if stage == "applied":
        if followup_count >= CADENCE["applied_max_followups"]:
            return None  # cold — no more follow-ups
        if followup_count == 0:
            if sent_d:
                return _add_days(sent_d, CADENCE["applied_first"])
            return None
        if last_d:
            return _add_days(last_d, CADENCE["applied_subsequent"])
        if sent_d:
            return _add_days(sent_d, CADENCE["applied_first"])
        return None

    if stage == "responded":
        if last_d:
            return _add_days(last_d, CADENCE["responded_subsequent"])
        if sent_d:
            return _add_days(sent_d, CADENCE["responded_subsequent"])
        return None

    if stage == "interview":
        if sent_d:
            return _add_days(sent_d, CADENCE["interview_thankyou"])
        return None

    return None


# ---------------------------------------------------------------------------
# Schema helpers — gracefully handle missing columns
# ---------------------------------------------------------------------------


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check whether *table* has a column named *column*."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    col_names = {r[1] if isinstance(r, tuple) else r["name"] for r in rows}
    return column in col_names


def _ensure_followup_columns(conn: sqlite3.Connection) -> bool:
    """Add followup_count and last_followup_at to email_outreach if missing.

    Returns True if the columns exist (either already or after migration).
    """
    has_count = _has_column(conn, "email_outreach", "followup_count")
    has_last = _has_column(conn, "email_outreach", "last_followup_at")

    if not has_count:
        try:
            conn.execute(
                "ALTER TABLE email_outreach ADD COLUMN followup_count INTEGER DEFAULT 0"
            )
            conn.commit()
            has_count = True
        except sqlite3.OperationalError:
            pass

    if not has_last:
        try:
            conn.execute(
                "ALTER TABLE email_outreach ADD COLUMN last_followup_at TEXT"
            )
            conn.commit()
            has_last = True
        except sqlite3.OperationalError:
            pass

    return has_count and has_last


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------


def analyze_followups(conn: sqlite3.Connection) -> dict:
    """Analyse all sent outreach emails and compute follow-up urgency.

    Returns a dict with keys ``metadata``, ``entries``, and ``cadence_config``.
    """
    has_fu_cols = _ensure_followup_columns(conn)

    # Build SELECT — pull followup columns only if they exist
    if has_fu_cols:
        fu_select = ", COALESCE(eo.followup_count, 0) AS followup_count, eo.last_followup_at"
    else:
        fu_select = ", 0 AS followup_count, NULL AS last_followup_at"

    query = f"""
        SELECT
            eo.id          AS outreach_id,
            eo.recipient_email,
            eo.sent_at,
            eo.subject,
            pl.recipient_name,
            pl.company,
            pl.role,
            pl.stage
            {fu_select}
        FROM email_outreach eo
        LEFT JOIN pipeline_leads pl
            ON pl.outreach_id = eo.id
        WHERE eo.status = 'sent'
        ORDER BY eo.sent_at ASC
    """

    rows = conn.execute(query).fetchall()

    today_d = date.today()
    entries: list[dict] = []

    for row in rows:
        # Unpack — support both Row and tuple
        if isinstance(row, sqlite3.Row):
            r = dict(row)
        else:
            r = dict(
                outreach_id=row[0],
                recipient_email=row[1],
                sent_at=row[2],
                subject=row[3],
                recipient_name=row[4],
                company=row[5],
                role=row[6],
                stage=row[7],
                followup_count=row[8],
                last_followup_at=row[9],
            )

        stage = r.get("stage") or "applied"
        sent_at = r.get("sent_at")
        sent_d = _parse_date(sent_at)
        days_since_sent = (today_d - sent_d).days if sent_d else 0

        followup_count = r.get("followup_count") or 0
        last_followup_at = r.get("last_followup_at")
        last_d = _parse_date(last_followup_at)
        days_since_last_followup = (today_d - last_d).days if last_d else None

        urgency = compute_urgency(stage, days_since_sent, days_since_last_followup, followup_count)

        # Skip non-actionable stages
        if stage not in ACTIONABLE_STAGES:
            continue

        next_followup_date = compute_next_followup_date(
            stage, sent_at, last_followup_at, followup_count
        )
        next_d = _parse_date(next_followup_date)
        days_until_next = (next_d - today_d).days if next_d else None

        entries.append(
            {
                "outreach_id": r["outreach_id"],
                "recipient_email": r["recipient_email"],
                "recipient_name": r.get("recipient_name") or "",
                "company": r.get("company") or "",
                "role": r.get("role") or "",
                "stage": stage,
                "sent_at": sent_at or "",
                "days_since_sent": days_since_sent,
                "followup_count": followup_count,
                "urgency": urgency,
                "next_followup_date": next_followup_date,
                "days_until_next": days_until_next,
            }
        )

    # Sort by urgency priority: urgent > overdue > waiting > cold
    urgency_order = {"urgent": 0, "overdue": 1, "waiting": 2, "cold": 3}
    entries.sort(key=lambda e: urgency_order.get(e["urgency"], 9))

    metadata = {
        "total_sent": len(entries),
        "actionable": sum(1 for e in entries if e["urgency"] in ("urgent", "overdue")),
        "overdue": sum(1 for e in entries if e["urgency"] == "overdue"),
        "urgent": sum(1 for e in entries if e["urgency"] == "urgent"),
        "cold": sum(1 for e in entries if e["urgency"] == "cold"),
        "waiting": sum(1 for e in entries if e["urgency"] == "waiting"),
    }

    return {
        "metadata": metadata,
        "entries": entries,
        "cadence_config": CADENCE,
    }


# ---------------------------------------------------------------------------
# Record a follow-up
# ---------------------------------------------------------------------------


def record_followup(conn: sqlite3.Connection, outreach_id: int) -> dict:
    """Record that a follow-up was sent for the given outreach entry.

    Increments ``followup_count`` and sets ``last_followup_at`` to now.
    Returns a dict with the updated values.
    """
    _ensure_followup_columns(conn)

    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Read current count
    row = conn.execute(
        "SELECT COALESCE(followup_count, 0) AS fc FROM email_outreach WHERE id = ?",
        (outreach_id,),
    ).fetchone()

    if row is None:
        raise ValueError(f"No email_outreach entry with id={outreach_id}")

    new_count = (row[0] if isinstance(row, tuple) else row["fc"]) + 1

    conn.execute(
        "UPDATE email_outreach SET followup_count = ?, last_followup_at = ? WHERE id = ?",
        (new_count, now_iso, outreach_id),
    )
    conn.commit()

    return {
        "outreach_id": outreach_id,
        "followup_count": new_count,
        "last_followup_at": now_iso,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_dashboard(report: dict) -> None:
    """Pretty-print the follow-up cadence dashboard."""
    meta = report["metadata"]
    entries = report["entries"]

    print()
    print("=" * 70)
    print(f"  Follow-up Cadence Dashboard — {date.today().isoformat()}")
    print(f"  {meta['total_sent']} sent emails tracked, {meta['actionable']} actionable")
    print("=" * 70)
    print()

    if not entries:
        print("  No sent outreach to track yet.")
        print()
        return

    print(
        f"  {meta['urgent']} urgent | {meta['overdue']} overdue"
        f" | {meta['waiting']} waiting | {meta['cold']} cold"
    )
    print()

    # Table header
    hdr = (
        "  "
        + "ID".ljust(6)
        + "Recipient".ljust(26)
        + "Company".ljust(16)
        + "Stage".ljust(12)
        + "Days".ljust(6)
        + "F/U".ljust(5)
        + "Next".ljust(13)
        + "Urgency"
    )
    print(hdr)
    print("  " + "-" * 84)

    for e in entries:
        name_or_email = e["recipient_name"] or e["recipient_email"]
        next_str = e["next_followup_date"] or "-"
        urgency_label = e["urgency"].upper() if e["urgency"] in ("urgent", "overdue", "cold") else e["urgency"]
        print(
            "  "
            + str(e["outreach_id"]).ljust(6)
            + name_or_email[:25].ljust(26)
            + (e["company"][:15] if e["company"] else "-").ljust(16)
            + e["stage"].ljust(12)
            + str(e["days_since_sent"]).ljust(6)
            + str(e["followup_count"]).ljust(5)
            + next_str.ljust(13)
            + urgency_label
        )

    print()


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Follow-up cadence tracker")
    parser.add_argument("--summary", action="store_true", help="Human-readable dashboard")
    parser.add_argument("--overdue-only", action="store_true", help="Show only overdue/urgent entries")
    parser.add_argument("--record", type=int, metavar="OUTREACH_ID", help="Record a follow-up for an outreach entry")
    parser.add_argument("--db", type=str, default=None, help="Path to SQLite database")
    args = parser.parse_args()

    db_path = args.db or DB_PATH
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row

    if args.record:
        result = record_followup(conn, args.record)
        print(json.dumps(result, indent=2))
    else:
        report = analyze_followups(conn)

        if args.overdue_only:
            report["entries"] = [
                e for e in report["entries"] if e["urgency"] in ("overdue", "urgent")
            ]

        if args.summary:
            _print_dashboard(report)
        else:
            print(json.dumps(report, indent=2, default=str))

    conn.close()
