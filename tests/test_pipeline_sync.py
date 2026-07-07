import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

import db  # noqa: E402
from routes import pipeline  # noqa: E402


class PipelineSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = db.init_db(Path(self.tmp.name) / "test.db")
        pipeline._local.conn = self.conn

    def tearDown(self):
        self.conn.close()
        pipeline._local.conn = None
        self.tmp.cleanup()

    def _insert_post(self, author_name="Hiring Manager"):
        cur = self.conn.execute(
            """INSERT INTO posts (post_url, content_hash, author_name, content)
               VALUES (?, ?, ?, ?)""",
            ("https://example.test/post", "hash-1", author_name, "We are hiring"),
        )
        return cur.lastrowid

    def _insert_job(self, post_id, role="AI Engineer", company="Acme Health", location="Remote"):
        self.conn.execute(
            "INSERT INTO jobs (post_id, role, company, location) VALUES (?, ?, ?, ?)",
            (post_id, role, company, location),
        )

    def _insert_outreach(
        self,
        *,
        post_id=None,
        recipient_email="talent@example.com",
        subject="AI Engineer | Your Skills Match",
        status="sent",
        sent_at="2026-05-08 10:00:00",
        reply_type=None,
        reply_preview=None,
        role=None,
        company=None,
        location=None,
        error_type=None,
        error_message=None,
    ):
        cur = self.conn.execute(
            """INSERT INTO email_outreach
               (post_id, recipient_email, subject, body, status, sent_at, reply_type,
                reply_preview, role, company, location, error_type, error_message)
               VALUES (?, ?, ?, 'hello', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                post_id,
                recipient_email,
                subject,
                status,
                sent_at,
                reply_type,
                reply_preview,
                role,
                company,
                location,
                error_type,
                error_message,
            ),
        )
        return cur.lastrowid

    def _lead_count(self):
        return self.conn.execute("SELECT COUNT(*) FROM pipeline_leads").fetchone()[0]

    def _lead(self):
        row = self.conn.execute("SELECT * FROM pipeline_leads ORDER BY id LIMIT 1").fetchone()
        return dict(row) if row else None

    def test_new_sent_email_becomes_applied_pipeline_lead(self):
        post_id = self._insert_post()
        self._insert_job(post_id)
        outreach_id = self._insert_outreach(post_id=post_id)
        self.conn.commit()

        result = pipeline.api_pipeline_sync()

        lead = self._lead()
        self.assertEqual(result["synced"], 1)
        self.assertEqual(lead["outreach_id"], outreach_id)
        self.assertEqual(lead["stage"], "applied")
        self.assertEqual(lead["role"], "AI Engineer")
        self.assertEqual(lead["company"], "Acme Health")

    def test_new_replied_email_sets_replied_or_rejected_stage(self):
        self._insert_outreach(
            recipient_email="recruiter@replyco.com",
            status="replied",
            reply_type="positive",
            reply_preview="Can we schedule a call?",
        )
        self._insert_outreach(
            recipient_email="jobs@rejectco.com",
            status="replied",
            reply_type="rejection",
            reply_preview="We moved ahead with other candidates.",
        )
        self.conn.commit()

        pipeline.api_pipeline_sync()

        rows = self.conn.execute(
            "SELECT recipient_email, stage FROM pipeline_leads ORDER BY recipient_email"
        ).fetchall()
        stages = {row["recipient_email"]: row["stage"] for row in rows}
        self.assertEqual(stages["jobs@rejectco.com"], "rejected")
        self.assertEqual(stages["recruiter@replyco.com"], "replied")

    def test_sync_is_idempotent(self):
        self._insert_outreach(recipient_email="talent@idempotent.com")
        self.conn.commit()

        first = pipeline.api_pipeline_sync()
        second = pipeline.api_pipeline_sync()

        self.assertEqual(first["synced"], 1)
        self.assertEqual(second["synced"], 0)
        self.assertEqual(self._lead_count(), 1)
        event_count = self.conn.execute("SELECT COUNT(*) FROM pipeline_events").fetchone()[0]
        self.assertEqual(event_count, 1)

    def test_pasted_outreach_without_post_preserves_own_metadata(self):
        self._insert_outreach(
            post_id=None,
            recipient_email="founder@startup.example",
            subject="Generic fallback subject",
            role="Founding AI Engineer",
            company="CarePilot",
            location="Bengaluru",
        )
        self.conn.commit()

        pipeline.api_pipeline_sync()

        lead = self._lead()
        self.assertEqual(lead["role"], "Founding AI Engineer")
        self.assertEqual(lead["company"], "CarePilot")
        self.assertEqual(lead["location"], "Bengaluru")

    def test_existing_applied_lead_gets_reply_stage_and_one_reply_event(self):
        outreach_id = self._insert_outreach(
            recipient_email="lead@reply.test",
            status="replied",
            reply_type="positive",
            reply_preview="Looks interesting.",
        )
        self.conn.execute(
            """INSERT INTO pipeline_leads
               (outreach_id, recipient_email, stage, company)
               VALUES (?, ?, 'applied', ?)""",
            (outreach_id, "lead@reply.test", "Reply"),
        )
        self.conn.commit()

        pipeline.api_pipeline_sync()
        pipeline.api_pipeline_sync()

        lead = self._lead()
        self.assertEqual(lead["stage"], "replied")
        reply_events = self.conn.execute(
            "SELECT COUNT(*) FROM pipeline_events WHERE lead_id = ? AND event_type = 'email_reply'",
            (lead["id"],),
        ).fetchone()[0]
        self.assertEqual(reply_events, 1)

    def test_offer_reply_sets_offer_stage(self):
        self._insert_outreach(
            recipient_email="akhil@startup.example",
            status="replied",
            reply_type="offer",
            reply_preview="Pleased to offer you the position. Offer letter attached.",
        )
        self.conn.commit()

        pipeline.api_pipeline_sync()

        lead = self._lead()
        self.assertEqual(lead["stage"], "offer")

    def test_offer_advances_already_interviewing_lead(self):
        # The exact bug: an offer arriving after the lead already moved past 'applied'.
        outreach_id = self._insert_outreach(
            recipient_email="akhil@startup.example",
            status="replied",
            reply_type="offer",
            reply_preview="We are pleased to offer you the role. Welcome aboard!",
        )
        self.conn.execute(
            """INSERT INTO pipeline_leads (outreach_id, recipient_email, stage, company)
               VALUES (?, ?, 'interviewing', ?)""",
            (outreach_id, "akhil@startup.example", "Startup"),
        )
        self.conn.commit()

        pipeline.api_pipeline_sync()

        lead = self._lead()
        self.assertEqual(lead["stage"], "offer")

    def test_interview_reply_sets_interviewing_stage(self):
        self._insert_outreach(
            recipient_email="hr@interviewco.com",
            status="replied",
            reply_type="interview",
            reply_preview="We'd like to schedule a technical interview. Share your availability.",
        )
        self.conn.commit()

        pipeline.api_pipeline_sync()

        lead = self._lead()
        self.assertEqual(lead["stage"], "interviewing")

    def test_offer_is_not_downgraded_by_later_rejection_signal(self):
        # Forward-only: once at 'offer', a stale 'replied' reply must not pull it back.
        outreach_id = self._insert_outreach(
            recipient_email="akhil@startup.example",
            status="replied",
            reply_type="positive",
            reply_preview="Thanks for the chat.",
        )
        self.conn.execute(
            """INSERT INTO pipeline_leads (outreach_id, recipient_email, stage, company)
               VALUES (?, ?, 'offer', ?)""",
            (outreach_id, "akhil@startup.example", "Startup"),
        )
        self.conn.commit()

        pipeline.api_pipeline_sync()

        lead = self._lead()
        self.assertEqual(lead["stage"], "offer")

    def test_existing_recipient_company_lead_is_not_duplicated(self):
        self.conn.execute(
            """INSERT INTO pipeline_leads
               (recipient_email, company, stage)
               VALUES ('hello@dupe.test', 'DupeCo', 'applied')"""
        )
        outreach_id = self._insert_outreach(
            recipient_email="hello@dupe.test",
            company="DupeCo",
            status="sent",
        )
        self.conn.commit()

        pipeline.api_pipeline_sync()

        self.assertEqual(self._lead_count(), 1)
        lead = self._lead()
        self.assertEqual(lead["outreach_id"], outreach_id)

    def test_bounced_outreach_does_not_create_lead_but_records_existing_event(self):
        self._insert_outreach(
            recipient_email="missing@bounce.test",
            status="failed",
            error_type="bounced",
            error_message="Address not found: missing@bounce.test",
        )
        existing_outreach = self._insert_outreach(
            recipient_email="linked@bounce.test",
            status="failed",
            error_type="bounced",
            error_message="Address not found: linked@bounce.test",
        )
        self.conn.execute(
            """INSERT INTO pipeline_leads
               (outreach_id, recipient_email, stage, company)
               VALUES (?, 'linked@bounce.test', 'applied', 'Bounce')""",
            (existing_outreach,),
        )
        self.conn.commit()

        pipeline.api_pipeline_sync()
        pipeline.api_pipeline_sync()

        self.assertEqual(self._lead_count(), 1)
        lead = self._lead()
        self.assertEqual(lead["stage"], "applied")
        bounce_events = self.conn.execute(
            "SELECT COUNT(*) FROM pipeline_events WHERE lead_id = ? AND event_type = 'email_bounced'",
            (lead["id"],),
        ).fetchone()[0]
        self.assertEqual(bounce_events, 1)


if __name__ == "__main__":
    unittest.main()
