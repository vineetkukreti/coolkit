"""Inbox tracker: storing job emails and advancing application outcomes.

Run: pytest tests/test_inbox_tracker.py -v
"""

import pytest

import db
from services import inbox_tracker as it


@pytest.fixture
def conn(tmp_path):
    return db.init_db(tmp_path / "t.db")


def _app(conn, company="Acme Health", title="AI Engineer", post_id=None):
    cur = conn.execute("INSERT INTO applications (platform, job_url, job_title, company, status, post_id) "
                       "VALUES ('linkedin', ?, ?, ?, 'applied', ?)", (f"https://x/{company}", title, company, post_id))
    conn.commit()
    return cur.lastrowid


def _outcome(conn, app_id):
    return conn.execute("SELECT outcome FROM applications WHERE id = ?", (app_id,)).fetchone()[0]


def test_rejection_sets_outcome_without_breaking_status_constraint(conn):
    app_id = _app(conn)
    entry = it.record_job_email(conn, "<m1>", "talent@acmehealth.com", "Your application to Acme Health",
                                "Unfortunately we will not be moving forward. We wish you the best.")
    assert entry["type"] == "rejection" and entry["matched_application"]["id"] == app_id
    assert _outcome(conn, app_id) == "rejected"
    assert conn.execute("SELECT status FROM applications WHERE id = ?", (app_id,)).fetchone()[0] == "applied"


def test_interview_advances_pipeline_and_never_downgrades(conn):
    conn.execute("INSERT INTO posts (id, post_url, content, content_hash) VALUES (7, 'https://p/7', 'x', 'h7')")
    conn.execute("INSERT INTO pipeline_leads (post_id, recipient_email, stage) VALUES (7, 'hr@acmehealth.com', 'applied')")
    app_id = _app(conn, post_id=7)

    it.record_job_email(conn, "<m1>", "hr@acmehealth.com", "Interview invitation - Acme Health",
                        "We'd like to schedule an interview. Please share your availability.")
    assert _outcome(conn, app_id) == "interviewing"
    assert conn.execute("SELECT stage FROM pipeline_leads WHERE post_id = 7").fetchone()[0] == "interviewing"

    # A late "thanks for applying" confirmation must not undo the interview
    it.record_job_email(conn, "<m2>", "noreply@acmehealth.com", "Thank you for applying to Acme Health", "We received your application.")
    assert _outcome(conn, app_id) == "interviewing"


def test_duplicate_message_ids_are_ignored(conn):
    _app(conn)
    args = ("<same>", "talent@acmehealth.com", "Acme Health update", "Unfortunately, not moving forward.")
    assert it.record_job_email(conn, *args)
    assert it.record_job_email(conn, *args) is None
    assert len(it.list_job_emails(conn)) == 1


def test_irrelevant_email_not_stored(conn):
    assert it.record_job_email(conn, "<n>", "friend@gmail.com", "Dinner?", "See you at 8") is None
    assert it.list_job_emails(conn) == []


def test_company_match_is_whole_word(conn):
    _app(conn, company="Meta", title="Research Engineer at Meta")
    entry = it.record_job_email(conn, "<x>", "noreply@jobs.example.com", "Application received",
                                "Thank you for applying. Your metadata has been saved.")
    assert entry["matched_application"] is None


def test_handled_emails_hidden_by_default(conn):
    _app(conn)
    it.record_job_email(conn, "<h>", "hr@acmehealth.com", "Interview with Acme Health", "Let's schedule an interview.")
    email_id = it.list_job_emails(conn)[0]["id"]
    assert it.set_job_email_handled(conn, email_id)
    assert it.list_job_emails(conn) == []
    assert len(it.list_job_emails(conn, include_handled=True)) == 1
