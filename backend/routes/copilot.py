"""Career copilot routes — cover letters, salary, LinkedIn, mock interviews, goals, extension."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from routes.tools import _get_db
from config import PROFILE

router = APIRouter()


def _bad(message: str, code: int = 400):
    return JSONResponse(status_code=code, content={"status": "error", "message": message})


def _llm_result(result: dict):
    if "error" in result:
        return _bad(result["error"], 502)
    return {"status": "ok", **result}


@router.post("/api/copilot/cover-letter")
def api_cover_letter(req: dict):
    from services.career_copilot import generate_cover_letter
    if not req.get("jd_text"):
        return _bad("jd_text required")
    return _llm_result(generate_cover_letter(req["jd_text"], req.get("company", ""), req.get("role", ""), req.get("tone", "professional")))


@router.post("/api/copilot/salary")
def api_salary(req: dict):
    from services.career_copilot import estimate_salary
    if not req.get("role"):
        return _bad("role required")
    years = req.get("experience_years")
    return _llm_result(estimate_salary(req["role"], req.get("company", ""), req.get("location", ""),
                                       float(years) if years not in (None, "") else None))


@router.post("/api/copilot/linkedin")
def api_linkedin(req: dict):
    from services.career_copilot import optimize_linkedin
    return _llm_result(optimize_linkedin(req.get("headline", ""), req.get("about", ""), req.get("target_role", "")))


@router.post("/api/copilot/mock-interview/question")
def api_mock_question(req: dict):
    from services.career_copilot import mock_interview_question
    if not req.get("company") or not req.get("role"):
        return _bad("company and role required")
    return _llm_result(mock_interview_question(req["company"], req["role"], req.get("round_type", "behavioral"), req.get("asked", [])))


@router.post("/api/copilot/mock-interview/grade")
def api_mock_grade(req: dict):
    from services.career_copilot import grade_interview_answer
    if not req.get("question") or not req.get("answer"):
        return _bad("question and answer required")
    return _llm_result(grade_interview_answer(req["question"], req["answer"], req.get("role", "")))


@router.get("/api/goals")
def api_goals():
    from services.career_copilot import get_goal_progress
    return get_goal_progress(_get_db())


@router.post("/api/goals")
def api_set_goals(req: dict):
    from services.career_copilot import set_goals
    try:
        return set_goals(_get_db(), req)
    except (TypeError, ValueError):
        return _bad("targets must be integers")


# ── Browser extension endpoints ─────────────────────────────────────────────

@router.post("/api/extension/save-job")
def api_extension_save_job(req: dict):
    from services.career_copilot import save_job_from_page
    if not req.get("url"):
        return _bad("url required")
    return save_job_from_page(_get_db(), req["url"], req.get("title", ""), req.get("company", ""),
                              req.get("location", ""), req.get("page_text", ""), req.get("status", "pending"))


@router.get("/api/extension/autofill-profile")
def api_extension_autofill_profile():
    """Flat field map the extension uses to fill ATS forms (Simplify-style)."""
    keys = ("first_name", "last_name", "name", "email", "phone", "location", "linkedin", "github", "website",
            "current_title", "employer", "experience_years", "notice_period_days", "desired_salary",
            "current_salary", "require_visa", "willing_to_relocate", "education", "education_level",
            "gender", "ethnicity", "disability_status", "veteran_status")
    return {"status": "ok", "profile": {k: PROFILE.get(k, "") for k in keys}}


# ── Answer bank (custom application questions) ──────────────────────────────

@router.post("/api/extension/answer-questions")
def api_answer_questions(req: dict):
    from services.answer_bank import answer_questions
    questions = req.get("questions") or []
    if not isinstance(questions, list) or not questions:
        return _bad("questions required")
    return answer_questions(_get_db(), questions[:60], req.get("company", ""), req.get("role", ""), req.get("jd_text", ""))


@router.post("/api/extension/remember-answers")
def api_remember_answers(req: dict):
    from services.answer_bank import remember
    saved = remember(_get_db(), req.get("answers") or [], req.get("company", ""))
    return {"status": "ok", "message": f"Remembered {saved} answer(s)", "saved": saved}


@router.get("/api/answer-bank")
def api_answer_bank():
    from services.answer_bank import list_answers
    answers = list_answers(_get_db())
    return {"status": "ok", "answers": answers, "total": len(answers)}


@router.delete("/api/answer-bank/{answer_id}")
def api_delete_answer(answer_id: int):
    from services.answer_bank import delete_answer
    if not delete_answer(_get_db(), answer_id):
        return _bad("not found", 404)
    return {"status": "ok"}


# ── Job inbox ───────────────────────────────────────────────────────────────

@router.get("/api/inbox/emails")
def api_inbox_emails(type: str = "", include_handled: bool = False):
    from services.inbox_tracker import list_job_emails
    emails = list_job_emails(_get_db(), email_type=type, include_handled=include_handled)
    return {"status": "ok", "emails": emails, "total": len(emails)}


@router.post("/api/inbox/emails/{email_id}/handled")
def api_inbox_email_handled(email_id: int, req: dict | None = None):
    from services.inbox_tracker import set_job_email_handled
    if not set_job_email_handled(_get_db(), email_id, (req or {}).get("handled", True)):
        return _bad("not found", 404)
    return {"status": "ok"}


@router.post("/api/inbox/emails/{email_id}/draft-reply")
def api_inbox_draft_reply(email_id: int):
    from services.career_copilot import draft_email_reply
    from services.inbox_tracker import _ensure_job_emails_table
    conn = _get_db()
    _ensure_job_emails_table(conn)
    row = conn.execute("SELECT subject, preview, type, from_addr FROM job_emails WHERE id = ?", (email_id,)).fetchone()
    if not row:
        return _bad("not found", 404)
    return _llm_result(draft_email_reply(row["subject"], row["preview"], row["type"], row["from_addr"]))
