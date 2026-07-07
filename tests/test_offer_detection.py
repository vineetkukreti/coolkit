"""Offer-detection tests — simulate real offer emails through the classifiers.

Covers the gap where a genuine job offer was never auto-detected and the pipeline
lead stayed stuck at 'applied'/'replied' instead of advancing to 'offer'.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from services.email_service import _classify_reply, _stage_from_reply_type  # noqa: E402
from services.inbox_tracker import classify_inbox_email  # noqa: E402


# A realistic offer email like the one from "Akhil's" system that went undetected.
AKHIL_OFFER = (
    "Hi Selva,\n\n"
    "Congratulations! We are pleased to offer you the position of AI Engineer at our company. "
    "Please find your offer letter attached. Your annual CTC is 28 LPA and the tentative date "
    "of joining is 1st July 2026. Looking forward to welcoming you aboard!\n\n"
    "Best regards,\nAkhil"
)


class ClassifyReplyOfferTests(unittest.TestCase):
    def test_akhil_offer_is_detected(self):
        self.assertEqual(_classify_reply(AKHIL_OFFER, "Your Offer Letter — AI Engineer"), "offer")

    def test_plain_offer_phrases(self):
        cases = [
            "We would like to offer you the position of Backend Engineer.",
            "Please find attached your offer of employment.",
            "Delighted to extend a formal offer. Welcome to the team!",
            "Your offer letter is attached. CTC of 30 LPA, joining date 15th July.",
            "We are happy to offer you this role. Welcome aboard!",
        ]
        for body in cases:
            with self.subTest(body=body):
                self.assertEqual(_classify_reply(body, ""), "offer")

    def test_real_akhil_salary_structure_email(self):
        body = (
            "Dear Vineet, we are pleased to confirm that we have aligned with the compensation "
            "figure shared by you and incorporated the same in the proposed salary structure. "
            "The Date of Joining has been mutually agreed to be 30-40 days from the issuance of "
            "the Letter of Intent (LOI). Please review the proposed salary structure and confirm "
            "your acceptance. Salary Structure Basic Salary 35280 House Rent Allowance (HRA) 17640"
        )
        self.assertEqual(_classify_reply(body, "Salary Structure and Date Of Joining- Akhil Systems"), "offer")

    def test_real_diagnuvo_letter_of_engagement(self):
        body = (
            "Following your acceptance of the Founding AI Engineer proposal, I've prepared the "
            "formal Letter of Engagement for execution. Position: Founding AI Engineer. "
            "Equity: Up to 1.0% fully diluted. Vesting: 24 months, 3-month cliff."
        )
        self.assertEqual(_classify_reply(body, "Letter of Engagement — Ready for Signature"), "offer")

    def test_offer_word_in_rejection_stays_rejection(self):
        # "unable to offer" must NOT be read as an offer.
        body = "Unfortunately, we regret to inform you that we are unable to offer you the role."
        self.assertEqual(_classify_reply(body, ""), "rejection")

    def test_offer_of_interview_is_not_a_job_offer(self):
        # Soft "offer" language attached to an interview must classify as interview, not offer.
        body = "We are pleased to offer you an interview. Can you schedule a call this week?"
        self.assertEqual(_classify_reply(body, ""), "interview")

    def test_interview_emails_are_detected(self):
        cases = [
            "We'd like to invite you for an interview. Please share your availability.",
            "You have been shortlisted. Next round is a technical assessment.",
            "Please complete the online assessment via the link below.",
            "Let's schedule a call — here is my Calendly.",
            "Invitation: Zoom meeting for your technical round on Thursday.",
            "Can you confirm your availability for a phone screen this week?",
        ]
        for body in cases:
            with self.subTest(body=body):
                self.assertEqual(_classify_reply(body, ""), "interview")

    def test_interview_maps_to_interviewing_stage(self):
        self.assertEqual(_stage_from_reply_type("interview"), "interviewing")

    def test_vague_interest_is_not_interview(self):
        # Soft interest without scheduling/round language stays 'interested' → 'replied'.
        body = "Thanks for reaching out, your background looks relevant. We'll be in touch."
        self.assertEqual(_classify_reply(body, ""), "interested")

    def test_congratulations_alone_is_not_an_offer(self):
        body = "Congratulations on advancing to the next round! We'll be in touch about the interview."
        self.assertNotEqual(_classify_reply(body, ""), "offer")

    def test_stage_mapping(self):
        self.assertEqual(_stage_from_reply_type("offer"), "offer")
        self.assertEqual(_stage_from_reply_type("rejection"), "rejected")
        self.assertEqual(_stage_from_reply_type("interview"), "interviewing")
        self.assertEqual(_stage_from_reply_type("positive"), "replied")
        self.assertEqual(_stage_from_reply_type("auto_reply"), "applied")


class InboxClassifierOfferTests(unittest.TestCase):
    def test_inbox_offer_detected(self):
        result = classify_inbox_email(
            "Your Offer Letter", AKHIL_OFFER, "akhil@startup.example"
        )
        self.assertEqual(result["type"], "offer")

    def test_inbox_rejection_with_offer_word(self):
        result = classify_inbox_email(
            "Application update",
            "Unfortunately we are unable to offer you the role at this time.",
            "hr@company.example",
        )
        self.assertEqual(result["type"], "rejection")


if __name__ == "__main__":
    unittest.main()
