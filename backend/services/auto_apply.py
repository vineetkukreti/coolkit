"""
Auto-Apply Engine
-----------------
Automated job application system supporting multiple apply methods:
- LinkedIn Easy Apply (Playwright automation)
- Email application (resume + cover letter via SMTP)
- Redirect/manual (opens URL, logs for manual follow-up)

Usage:
    engine = AutoApplyEngine(conn, page)
    engine.run(max_applications=500)
"""

import os
import re
import random
import time
import threading
from datetime import datetime
from pathlib import Path

from config import PROFILE
from db import (
    init_db, application_exists, log_application,
    get_applied_urls, quota_remaining, get_unapplied_jobs,
    get_today_quota,
)

# ─── Platform budgets (daily) ─────────────────────────────────────────────

PLATFORM_BUDGETS = {
    "linkedin_easy_apply": 30,  # LinkedIn restricts accounts that apply much faster than this
    "email_apply": 180,
    "indeed": 30,
    "naukri": 30,
    "wellfound": 30,
    "other": 110,
}

# Rate limits per platform (seconds between applications)
RATE_LIMITS = {
    "linkedin_easy_apply": (45, 120),  # 25/hour max
    "email_apply": (10, 30),
    "indeed": (30, 60),
    "naukri": (30, 60),
    "default": (15, 45),
}


# ─── Auto-Apply State ────────────────────────────────────────────────────────

auto_apply_state = {
    "running": False,
    "status": "idle",  # idle | running | done | stopped | error
    "started_at": None,
    "progress": {
        "total_attempted": 0,
        "applied": 0,
        "failed": 0,
        "skipped": 0,
        "current_job": None,
    },
    "log": [],
    "review": True,          # stop at LinkedIn's Submit button and wait for the user
    "pending_review": None,  # {job, filled, needs_attention, since} while waiting
}

_apply_lock = threading.Lock()
_stop_flag = threading.Event()
_review_event = threading.Event()
_review_decision = {"decision": None}
REVIEW_TIMEOUT_S = 15 * 60


def _emit(event: dict):
    """Add event to auto-apply log."""
    with _apply_lock:
        auto_apply_state["log"].append({
            "time": datetime.now().isoformat(),
            **event,
        })
        # Keep last 500 events
        if len(auto_apply_state["log"]) > 500:
            auto_apply_state["log"] = auto_apply_state["log"][-500:]


# ─── Apply Methods ────────────────────────────────────────────────────────────

def _linkedin_warm_up(page, job: dict):
    """Simulate human browsing behavior before applying.
    Reduces bot detection risk by mimicking natural LinkedIn behavior.
    """
    try:
        # 1. Scroll down to read the job description (human behavior)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
        time.sleep(random.uniform(1.5, 3.0))

        # 2. Scroll a bit more — like reading the requirements
        page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.6)")
        time.sleep(random.uniform(2.0, 4.0))

        # 3. Scroll back up to the apply button area
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(random.uniform(1.0, 2.0))

        # 4. For premium tier jobs, try to view the company page briefly
        is_premium = (job.get("_tier") or {}).get("label") == "PREMIUM"
        if is_premium:
            try:
                company_link = page.query_selector(
                    'a[data-tracking-control-name="public_jobs_topcard-org-name"], '
                    'a.topcard__org-name-link, '
                    'a[href*="/company/"]'
                )
                if company_link:
                    company_link.click()
                    time.sleep(random.uniform(3.0, 5.0))
                    # Go back to the job page
                    page.go_back()
                    time.sleep(random.uniform(2.0, 3.0))
            except Exception:
                pass

    except Exception:
        pass  # Warm-up is best-effort, don't fail the application


_SUBMIT_SELECTOR = (
    'button[aria-label*="Submit application"], '
    'button[aria-label*="Submit"], '
    'button[data-easy-apply-next-button]:has-text("Submit")'
)
_NEXT_SELECTOR = (
    'button[aria-label*="Continue"], '
    'button[aria-label*="Next"], '
    'button[aria-label*="Review"], '
    'button[data-easy-apply-next-button], '
    'button:has-text("Next"), '
    'button:has-text("Review")'
)


def _easy_apply_prepare(page, job: dict) -> dict:
    """Open Easy Apply and fill every step, stopping AT the submit button (nothing is submitted).

    Runs on the browser thread. Returns {"status": "ready"|"failed", "method", "filled", "error"}.
    """
    url = job.get("apply_url") or job.get("post_url", "")
    if not url or "linkedin.com" not in url:
        return {"status": "failed", "method": "easy_apply", "error": "Not a LinkedIn URL"}
    job["_filled"] = []

    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        time.sleep(random.uniform(2, 4))
        _linkedin_warm_up(page, job)

        easy_apply_btn = page.query_selector('button[aria-label*="Easy Apply"], button.jobs-apply-button')
        if not easy_apply_btn:
            return {"status": "failed", "method": "easy_apply", "error": "No Easy Apply button found"}
        easy_apply_btn.click()
        time.sleep(random.uniform(2, 3))

        for _ in range(10):
            _fill_form_fields(page, job_context=job)
            time.sleep(random.uniform(1, 2))

            submit_btn = page.query_selector(_SUBMIT_SELECTOR)
            if submit_btn and submit_btn.is_visible():
                return {"status": "ready", "method": "easy_apply", "filled": job["_filled"]}

            next_btn = page.query_selector(_NEXT_SELECTOR)
            if not next_btn:
                break
            next_btn.click()
            time.sleep(random.uniform(1.5, 2.5))
            # LinkedIn keeps you on the same step and shows inline errors when a required field is empty
            if page.query_selector('.artdeco-inline-feedback--error, [data-test-form-element-error-messages]'):
                _fill_form_fields(page, job_context=job)
                next_btn = page.query_selector(_NEXT_SELECTOR)
                if next_btn:
                    next_btn.click()
                    time.sleep(random.uniform(1.5, 2.5))
                if page.query_selector('.artdeco-inline-feedback--error, [data-test-form-element-error-messages]'):
                    return {"status": "failed", "method": "easy_apply", "filled": job["_filled"],
                            "error": "Required question could not be answered"}

        return {"status": "failed", "method": "easy_apply", "filled": job["_filled"], "error": "Could not reach submit step"}

    except Exception as e:
        return {"status": "failed", "method": "easy_apply", "filled": job.get("_filled", []), "error": str(e)[:200]}


def _easy_apply_finish(page, submit: bool) -> dict:
    """Submit the prepared application, or discard it. Runs on the browser thread."""
    try:
        if not submit:
            dismiss = page.query_selector('button[aria-label="Dismiss"], button[data-test-modal-close-btn]')
            if dismiss:
                dismiss.click()
                time.sleep(1)
                discard = page.query_selector('button[data-control-name="discard_application_confirm_btn"], '
                                              'button:has-text("Discard")')
                if discard:
                    discard.click()
            return {"status": "skipped", "method": "easy_apply"}

        submit_btn = page.query_selector(_SUBMIT_SELECTOR)
        if not submit_btn:
            return {"status": "failed", "method": "easy_apply", "error": "Submit button disappeared"}
        submit_btn.click()
        time.sleep(random.uniform(2.5, 3.5))

        confirmed = page.query_selector(
            'h2:has-text("application was sent"), h3:has-text("application was sent"), '
            'h2:has-text("applied"), button:has-text("Done")'
        )
        if not confirmed:
            # Don't record a success we didn't see
            return {"status": "failed", "method": "easy_apply", "error": "Submitted but LinkedIn showed no confirmation"}
        try:
            close = page.query_selector('button:has-text("Done"), button[aria-label="Dismiss"]')
            if close:
                close.click()
        except Exception:
            pass
        return {"status": "applied", "method": "easy_apply"}
    except Exception as e:
        return {"status": "failed", "method": "easy_apply", "error": str(e)[:200]}


def _fill_form_fields(page, job_context: dict = None):
    """Fill common Easy Apply form fields from PROFILE config."""
    field_map = {
        'input[name*="phone"], input[aria-label*="phone"], input[id*="phone"]': PROFILE.get("phone", ""),
        'input[name*="city"], input[aria-label*="city"], input[id*="city"]': PROFILE.get("location", "India"),
    }

    for selector, value in field_map.items():
        if not value:
            continue
        try:
            field = page.query_selector(selector)
            if field and field.is_visible():
                current = field.input_value()
                if not current:
                    field.fill(value)
        except Exception:
            pass

    # Handle resume upload if needed (uses best variant for this job)
    try:
        upload = page.query_selector('input[type="file"]')
        if upload:
            from services.resume_selector import get_resume_for_job
            resume_path = Path(get_resume_for_job(job_context))
            if not resume_path.exists():
                resume_path = Path(PROFILE.get("resume_path", "assets/resumes/default/resume.pdf"))
            if resume_path.exists():
                upload.set_input_files(str(resume_path))
    except Exception:
        pass

    # Handle text areas and custom questions (LLM-powered)
    _handle_text_questions(page, job_context=job_context)

    _handle_dropdowns(page, job_context)
    _handle_radio_buttons(page, job_context)
    _handle_numeric_inputs(page, job_context)


def _handle_text_questions(page, job_context: dict = None):
    """Fill text areas and custom text inputs: answer bank -> profile -> AI (AI only for higher tiers)."""
    skip_patterns = ["phone", "city", "email", "name", "first", "last",
                     "zip", "postal", "address", "url", "linkedin", "github",
                     "website", "search"]
    try:
        for el in page.query_selector_all('textarea, input[type="text"]'):
            if not el.is_visible() or el.input_value() or el.get_attribute("role") == "combobox":
                continue
            question = _get_field_label(page, el)
            if not question:
                continue
            is_textarea = el.evaluate("e => e.tagName") == "TEXTAREA"
            if not is_textarea and any(skip in question.lower() for skip in skip_patterns):
                continue
            answer, source = _resolve_answer(question, job_context)
            try:
                if answer:
                    el.fill(answer if is_textarea else answer[:200], timeout=5000)
                    time.sleep(random.uniform(0.2, 0.6))
            except Exception:
                answer, source = "", "missing"
            _record(job_context, question, answer, source)
    except Exception:
        pass


def _handle_numeric_inputs(page, job_context: dict = None):
    """Fill numeric fields (salary, notice period, years) via the same resolver."""
    try:
        for inp in page.query_selector_all('input[type="number"]'):
            if not inp.is_visible() or inp.input_value():
                continue
            question = _get_field_label(page, inp)
            if not question:
                continue
            answer, source = _resolve_answer(question, job_context)
            number = re.search(r"\d+(?:\.\d+)?", answer or "")
            if number:
                try:
                    inp.fill(number.group(0), timeout=5000)
                except Exception:
                    number = None
            _record(job_context, question, number.group(0) if number else "", source if number else "missing")
    except Exception:
        pass


def _get_field_label(page, element) -> str:
    """Extract the label/question text for a form field."""
    try:
        # Method 1: aria-label
        label = element.get_attribute("aria-label")
        if label and len(label) > 3:
            return label.strip()

        # Method 2: associated <label> via for/id
        field_id = element.get_attribute("id")
        if field_id:
            label_el = page.query_selector(f'label[for="{field_id}"]')
            if label_el:
                return label_el.inner_text().strip()

        # Method 3: parent label
        parent_label = element.evaluate("""el => {
            let parent = el.closest('label');
            if (parent) return parent.textContent.trim();
            // Try parent div's previous sibling or label
            let container = el.closest('.fb-dash-form-element, .jobs-easy-apply-form-element, div[data-test-form-element]');
            if (container) {
                let lbl = container.querySelector('label, legend, span.fb-dash-form-element__label, .t-14');
                if (lbl) return lbl.textContent.trim();
            }
            // Walk up to find nearby label text
            let prev = el.parentElement;
            for (let i = 0; i < 3 && prev; i++) {
                let lbl = prev.querySelector('label, legend, .t-bold');
                if (lbl && lbl.textContent.trim().length > 3) return lbl.textContent.trim();
                prev = prev.parentElement;
            }
            return '';
        }""")
        if parent_label and len(parent_label) > 3:
            return parent_label

        # Method 4: placeholder
        placeholder = element.get_attribute("placeholder")
        if placeholder and len(placeholder) > 3:
            return placeholder

    except Exception:
        pass
    return ""


# ─── LLM-powered answer cache (avoid duplicate API calls per session) ────────

_answer_cache = {}
_answer_cache_lock = threading.Lock()


def _bank_lookup(question: str, company: str) -> str:
    """Look the question up in the user's answer bank (answers they approved before)."""
    try:
        from services.answer_bank import lookup
        conn = init_db()
        try:
            hit = lookup(conn, question, company)
            conn.commit()
            return hit["answer"] if hit else ""
        finally:
            conn.close()
    except Exception:
        return ""


def _resolve_answer(question: str, job_context: dict | None, options: list | None = None) -> tuple[str, str]:
    """Return (answer, source). Source is 'bank', 'profile' or 'ai'; ('', 'missing') if unanswerable.

    With options, the answer is mapped onto one of them or dropped — never a guess outside the list.
    """
    from services.answer_bank import _match_option

    job_context = job_context or {}
    company = job_context.get("company", "")
    candidates = [
        (lambda: _bank_lookup(question, company), "bank"),
        (lambda: _get_known_answer(question.lower().strip()), "profile"),
        (lambda: _llm_answer_question(question, job_context, options), "ai"),
    ]
    for get, source in candidates:
        if source == "ai" and not (job_context.get("_use_llm") or options):
            continue
        answer = (get() or "").strip()
        if not answer:
            continue
        if options:
            answer = _match_option(answer, options) or ""
            if not answer:
                continue
        return answer, source
    return "", "missing"


def _record(job_context: dict | None, question: str, answer: str, source: str):
    if job_context is not None:
        job_context.setdefault("_filled", []).append({"question": question[:300], "answer": answer, "source": source})


def _answer_form_question(question: str, job_context: dict = None) -> str:
    """Backward-compatible wrapper: answer text only."""
    return _resolve_answer(question, job_context)[0]


def _get_known_answer(question_lower: str) -> str:
    """Answers that come straight from the profile (no LLM). Empty string when the profile doesn't say."""
    exp = PROFILE.get("experience_years")
    needs_visa = str(PROFILE.get("require_visa", "")).strip()

    if any(kw in question_lower for kw in ["sponsorship", "require visa", "need visa"]):
        return needs_visa or ""
    if any(kw in question_lower for kw in ["authorized to work", "work authorization", "legally authorized", "eligible to work"]):
        # Only answer when the profile says no sponsorship is needed; otherwise leave it for review
        return "Yes" if needs_visa.lower() == "no" else ""
    if any(kw in question_lower for kw in ["salary", "compensation", "expected ctc", "pay expectation"]):
        return str(PROFILE["desired_salary"]) if PROFILE.get("desired_salary") else ""
    if "current ctc" in question_lower or "current salary" in question_lower:
        return str(PROFILE["current_salary"]) if PROFILE.get("current_salary") else ""
    if any(kw in question_lower for kw in ["notice period", "days to join", "when can you start"]):
        return f"{PROFILE['notice_period_days']}" if PROFILE.get("notice_period_days") is not None else ""
    if any(kw in question_lower for kw in ["years of experience", "total experience", "how many years"]):
        # Only total experience — "years of experience with Kubernetes" is skill-specific, leave it to bank/AI
        return str(exp) if exp and not re.search(r"\b(with|in|using)\b", question_lower) else ""
    if any(kw in question_lower for kw in ["willing to relocate", "open to relocation", "relocate"]):
        return PROFILE.get("willing_to_relocate", "")
    if "linkedin" in question_lower:
        return PROFILE.get("linkedin", "")
    if "github" in question_lower:
        return PROFILE.get("github", "")
    if any(kw in question_lower for kw in ["portfolio", "personal website"]):
        return PROFILE.get("website", "") or PROFILE.get("github", "")
    if any(kw in question_lower for kw in ["how did you hear", "where did you find", "how did you learn"]):
        return "LinkedIn"
    if any(kw in question_lower for kw in ["current company", "current employer", "present company"]):
        return PROFILE.get("employer", "")
    if any(kw in question_lower for kw in ["current title", "current role", "job title"]):
        return PROFILE.get("current_title", "")
    if any(kw in question_lower for kw in ["highest education", "degree", "qualification"]):
        return PROFILE.get("education_level", "")
    if "gender" in question_lower:
        return PROFILE.get("gender", "")
    if any(kw in question_lower for kw in ["ethnicity", "race"]):
        return PROFILE.get("ethnicity", "")
    if "disability" in question_lower:
        return PROFILE.get("disability_status", "")
    if "veteran" in question_lower:
        return PROFILE.get("veteran_status", "")
    return ""


def _llm_answer_question(question: str, job_context: dict = None, options: list | None = None) -> str:
    """Use Gemini to answer a custom form question based on profile + job context."""
    try:
        from services.ai_tools import _call_gemini

        role = (job_context or {}).get("role", "AI/ML role")
        company = (job_context or {}).get("company", "the company")
        content = (job_context or {}).get("content", "")[:500]

        from config import get_profile_context
        profile_ctx = get_profile_context()

        prompt = f"""Answer this job application form question concisely (2-4 sentences max).

QUESTION: {question}
{("OPTIONS (reply with exactly one of these): " + " | ".join(options)) if options else ""}

CANDIDATE:
{profile_ctx}

ROLE: {role} at {company}
JOB CONTEXT: {content[:300] if content else 'Not available'}

RULES:
- Be specific, confident, and concise
- Reference real experience, never invent
- No corporate-speak ("passionate about", "excited to")
- Lead with proof, not assertions
- 2-4 sentences max

Answer:"""

        answer = _call_gemini(prompt, max_tokens=200, temperature=0.4)
        # Clean up
        answer = answer.strip().strip('"').strip("'")
        if answer and (options or len(answer) > 10):
            return answer

    except Exception:
        pass
    return ""


def _handle_dropdowns(page, job_context: dict = None):
    """Answer <select> questions; the answer must be one of the real options or it's left for review."""
    try:
        for select in page.query_selector_all('select'):
            if not select.is_visible():
                continue
            current = select.evaluate("s => s.selectedIndex > 0 || (s.value && !/select an option/i.test(s.options[s.selectedIndex]?.text || ''))")
            if current:
                continue
            question = _get_field_label(page, select)
            options = [o for o in select.evaluate(
                "s => [...s.options].filter(o => o.value && !/select an option/i.test(o.text)).map(o => o.text.trim())") if o]
            if not question or not options:
                continue
            answer, source = _resolve_answer(question, job_context, options)
            try:
                if answer:
                    select.select_option(label=answer, timeout=5000)
            except Exception:
                answer, source = "", "missing"
            _record(job_context, question, answer, source)
    except Exception:
        pass


def _handle_radio_buttons(page, job_context: dict = None):
    """Answer radio-group questions (fieldsets) the same way as dropdowns."""
    try:
        for fs in page.query_selector_all('fieldset'):
            if not fs.is_visible():
                continue
            radios = fs.query_selector_all('input[type="radio"]')
            if not radios or any(r.is_checked() for r in radios):
                continue
            legend = fs.query_selector('legend')
            question = (legend.inner_text() if legend else "").strip()
            labels = fs.evaluate("""f => [...f.querySelectorAll('input[type=radio]')].map(r =>
                (r.id && f.querySelector(`label[for="${CSS.escape(r.id)}"]`)?.textContent || r.value || '').trim())""")
            if not question or not labels:
                continue
            answer, source = _resolve_answer(question, job_context, labels)
            try:
                if answer:
                    radios[labels.index(answer)].check(force=True, timeout=5000)
            except Exception:
                answer, source = "", "missing"
            _record(job_context, question, answer, source)
    except Exception:
        pass


def _email_apply(conn, job: dict) -> dict:
    """Send application email with resume attached.
    Uses Gemini-personalized email when possible, falls back to template.
    Returns {"status": "applied"|"failed", "method": "email", "error": ...}
    """
    email = job.get("email", "")
    if not email:
        return {"status": "failed", "method": "email", "error": "No email address"}

    # Take first email if multiple
    email = email.split(",")[0].strip()
    from services.email_service import validate_email_before_send
    check = validate_email_before_send(email)
    if not check["valid"]:
        return {"status": "failed", "method": "email", "error": check["reason"]}

    try:
        from services.email_service import send_email_with_resume

        role = job.get("role", "AI Engineer")
        company = job.get("company", "your company")

        # Use tier to decide personalization level
        should_personalize = job.get("_personalize", True)
        if should_personalize:
            subject, body = _generate_personalized_email(job)
        else:
            subject = f"Application: {role} at {company} — {PROFILE['name']}"
            body = _generate_template_email(job)

        # Select best resume variant for this job's archetype
        from services.resume_selector import get_resume_for_job
        resume_path = get_resume_for_job(job)

        result = send_email_with_resume(
            to_email=email,
            subject=subject,
            body=body,
            resume_path=resume_path,
        )

        if result.get("success"):
            # Auto-register in pipeline for follow-up tracking
            _register_for_followup(conn, job, email)
            return {"status": "applied", "method": "email", "personalized": True}
        else:
            return {"status": "failed", "method": "email", "error": result.get("error", "Send failed")}

    except Exception as e:
        return {"status": "failed", "method": "email", "error": str(e)[:200]}


def _generate_personalized_email(job: dict) -> tuple[str, str]:
    """Generate a personalized email using Gemini, fall back to template.
    Returns (subject, body) tuple.
    """
    role = job.get("role", "AI Engineer")
    company = job.get("company", "your company")

    # Try Gemini personalization using the full post content
    try:
        from services.email_service import _generate_email_with_gemini

        post_data = {
            "content": job.get("content", ""),
            "role": role,
            "company": company,
            "location": job.get("location", ""),
            "experience": job.get("experience", ""),
            "is_hiring": True,
            "domain_relevance": job.get("domain_relevance", ""),
            "author_name": "",  # not always available in auto-apply context
            "post_url": job.get("post_url", ""),
        }

        # Only try if we have meaningful content to personalize from
        if post_data["content"] and len(post_data["content"]) > 50:
            result = _generate_email_with_gemini(post_data)
            subject = result.get("subject", "")
            body = result.get("body", "")
            if subject and body and len(body) > 50:
                return subject, body
    except Exception:
        pass  # Fall through to template

    # Fallback: hardcoded template
    subject = f"Application: {role} at {company} — {PROFILE['name']}"
    body = _generate_template_email(job)
    return subject, body


def _generate_template_email(job: dict) -> str:
    """Fallback template email when Gemini is unavailable."""
    role = job.get("role", "the role")
    company = job.get("company", "your company")
    name = PROFILE["name"]

    title = PROFILE.get("current_title", "Engineer")
    exp = PROFILE.get("experience_years", 0)
    employer = PROFILE.get("employer", "")
    skills_summary = PROFILE.get("skills_summary", "")

    intro = f"I'm {name}"
    if title:
        intro += f", a {title}"
    if exp:
        intro += f" with {exp} years of experience"
    intro += "."

    current_line = ""
    if employer:
        current_line = f"\nCurrently at {employer}."
    if skills_summary:
        current_line += f" {skills_summary}" if current_line else f"\n{skills_summary}"

    body = f"""Hi,

{intro} I'm writing to express my interest in the {role} position at {company}.{current_line}

I've attached my resume for your review. I'd love to discuss how my experience aligns with what you're building.

Best,
{name}"""

    return body


def _redirect_apply(job: dict) -> dict:
    """Log job for manual application (no automation possible).
    Returns {"status": "pending", "method": "redirect"}
    """
    return {"status": "pending", "method": "redirect"}


def _register_for_followup(conn, job: dict, recipient_email: str):
    """Register a successful email application for follow-up tracking.
    Creates a pipeline_lead entry so the followup_cadence system can track it.
    """
    try:
        role = job.get("role", "")[:100]
        company = job.get("company", "")[:100]
        post_id = job.get("id")

        # Check if a pipeline lead already exists for this email+company
        existing = conn.execute(
            "SELECT id FROM pipeline_leads WHERE recipient_email = ? AND company = ?",
            (recipient_email, company),
        ).fetchone()

        if not existing:
            conn.execute(
                """INSERT INTO pipeline_leads
                   (post_id, recipient_email, role, company, stage, source)
                   VALUES (?, ?, ?, ?, 'applied', 'auto-apply')""",
                (post_id, recipient_email, role, company),
            )
            conn.commit()
    except Exception:
        pass  # Non-critical — don't fail the application


# ─── Main Engine ─────────────────────────────────────────────────────────────

# ─── Apply Tier Strategy ─────────────────────────────────────────────────────

APPLY_TIERS = {
    "premium":  {"min_score": 7.0, "personalize_email": True,  "use_llm_answers": True,  "label": "PREMIUM"},
    "standard": {"min_score": 5.0, "personalize_email": True,  "use_llm_answers": False, "label": "STANDARD"},
    "basic":    {"min_score": 3.5, "personalize_email": False, "use_llm_answers": False, "label": "BASIC"},
    # Below 3.5 → SKIP (handled in should_apply)
}


def _get_apply_tier(smart_score: float) -> dict:
    """Determine apply tier based on smart_score."""
    if smart_score is None:
        return APPLY_TIERS["standard"]  # No score = standard effort
    for tier in ["premium", "standard", "basic"]:
        if smart_score >= APPLY_TIERS[tier]["min_score"]:
            return APPLY_TIERS[tier]
    return None  # Below all thresholds = skip


class AutoApplyEngine:
    """Orchestrates automated job applications across platforms.
    Uses score-gated tiers to invest more effort in better matches."""

    def __init__(self, conn, page=None):
        self.conn = conn
        self.page = page  # Playwright page for LinkedIn Easy Apply
        self._applied_urls = get_applied_urls(conn)
        self._platform_counts = {}

    def should_apply(self, job: dict) -> tuple[bool, str]:
        """Pre-check: dedup, fitness, quota, smart_score, and liveness."""
        url = job.get("post_url") or job.get("apply_url") or ""
        if not url:
            return False, "no-url"
        if url in self._applied_urls:
            return False, "already-applied"
        if application_exists(self.conn, url):
            return False, "already-applied"
        if quota_remaining(self.conn) <= 0:
            return False, "daily-quota-reached"

        # Smart score gate: skip jobs below minimum threshold
        smart_score = job.get("smart_score")
        if smart_score is not None and smart_score < 3.5:
            return False, f"low-score:{smart_score:.1f}"

        # Liveness check: skip expired/dead postings (save quota)
        # Only check if the post has a URL and hasn't been checked recently
        is_live = job.get("is_live")
        if is_live is not None and str(is_live) == "0":
            return False, "expired-posting"
        if is_live is None and url:
            # Quick liveness check for unchecked posts
            try:
                from services.liveness import check_url_liveness
                result = check_url_liveness(url, timeout=8)
                if result.get("result") == "expired":
                    # Update DB so we don't re-check
                    try:
                        self.conn.execute("UPDATE posts SET is_live = 0 WHERE id = ?", (job.get("id"),))
                        self.conn.commit()
                    except Exception:
                        pass
                    return False, f"expired-posting:{result.get('reason', '')[:40]}"
                elif result.get("result") == "active":
                    try:
                        self.conn.execute("UPDATE posts SET is_live = 1 WHERE id = ?", (job.get("id"),))
                        self.conn.commit()
                    except Exception:
                        pass
            except Exception:
                pass  # Don't block on liveness errors

        return True, "ok"

    def _determine_method(self, job: dict) -> str:
        """Determine the best apply method for a job."""
        url = job.get("apply_url") or job.get("post_url", "")
        email = job.get("email", "")

        if "linkedin.com/jobs" in url and self.page:
            count = self._platform_counts.get("linkedin_easy_apply", 0)
            if count < PLATFORM_BUDGETS.get("linkedin_easy_apply", 120):
                return "linkedin_easy_apply"

        if email:
            count = self._platform_counts.get("email_apply", 0)
            if count < PLATFORM_BUDGETS.get("email_apply", 180):
                return "email_apply"

        return "redirect"

    def _easy_apply(self, job: dict) -> dict:
        """Fill the Easy Apply form on the browser thread, then submit (or wait for the user's review)."""
        from services.browser_service import _run_on_browser_thread
        from worker_ctx import current_uid, run_with_user

        uid = current_uid()
        on_browser = lambda fn, *args: _run_on_browser_thread(run_with_user(uid, fn, *args), timeout=300)

        prepared = on_browser(_easy_apply_prepare, self.page, job)
        if prepared["status"] != "ready":
            return prepared

        with _apply_lock:
            review = auto_apply_state["review"]
        if not review:
            return on_browser(_easy_apply_finish, self.page, True)

        filled = prepared.get("filled", [])
        needs_attention = [f for f in filled if f["source"] in ("ai", "missing")]
        _review_event.clear()
        _review_decision["decision"] = None
        with _apply_lock:
            auto_apply_state["status"] = "awaiting_review"
            auto_apply_state["pending_review"] = {
                "job": {"title": job.get("role", ""), "company": job.get("company", ""),
                        "url": job.get("apply_url") or job.get("post_url", ""), "smart_score": job.get("smart_score")},
                "filled": filled,
                "needs_attention": len(needs_attention),
                "since": datetime.now().isoformat(),
            }
        _emit({"type": "info", "message": f"Waiting for your review: {job.get('role', '?')[:30]} at {job.get('company', '?')[:25]}"})

        # Wake up periodically so Stop still works while waiting
        waited = 0
        while not _review_event.wait(timeout=2):
            waited += 2
            if _stop_flag.is_set() or waited >= REVIEW_TIMEOUT_S:
                break
        decision = _review_decision["decision"] or "skip"

        with _apply_lock:
            auto_apply_state["pending_review"] = None
            if auto_apply_state["status"] == "awaiting_review":
                auto_apply_state["status"] = "running"

        result = on_browser(_easy_apply_finish, self.page, decision == "submit")
        if result["status"] == "applied":
            self._remember_answers(job, filled)
        elif decision != "submit":
            result["error"] = "Skipped in review" if _review_decision["decision"] else "Review timed out"
        return result

    def _remember_answers(self, job: dict, filled: list):
        """Answers on an application the user approved become their answers for next time."""
        try:
            from services.answer_bank import remember
            remember(self.conn, [f for f in filled if f.get("answer")], company=job.get("company", ""))
        except Exception:
            pass

    def apply_one(self, job: dict) -> dict:
        """Apply to a single job with effort scaled by smart_score tier."""
        url = job.get("post_url") or job.get("apply_url") or ""
        method = self._determine_method(job)

        # Determine apply tier
        smart_score = job.get("smart_score")
        tier = _get_apply_tier(smart_score)
        tier_label = tier["label"] if tier else "SKIP"

        with _apply_lock:
            auto_apply_state["progress"]["current_job"] = {
                "title": job.get("role", "")[:40],
                "company": job.get("company", "")[:30],
                "method": method,
                "tier": tier_label,
                "smart_score": smart_score,
            }

        _emit({
            "type": "info",
            "message": f"[{tier_label}] Applying to {job.get('role', '?')[:25]} at {job.get('company', '?')[:20]} "
                       f"(score: {smart_score or '?'}, method: {method})",
        })

        # Execute the appropriate apply method with tier context
        # Store tier info in job for downstream functions
        job["_tier"] = tier
        job["_personalize"] = tier.get("personalize_email", False) if tier else False
        job["_use_llm"] = tier.get("use_llm_answers", False) if tier else False

        if method == "linkedin_easy_apply":
            result = self._easy_apply(job)
        elif method == "email_apply":
            result = _email_apply(self.conn, job)
        else:
            result = _redirect_apply(job)

        result["tier"] = tier_label
        result["smart_score"] = smart_score

        # Log the application
        log_application(
            self.conn,
            platform=job.get("source", "unknown"),
            job_url=url,
            job_title=job.get("role", ""),
            company=job.get("company", ""),
            location=job.get("location", ""),
            status=result["status"],
            apply_method=result["method"],
            post_id=job.get("id"),
            error_message=result.get("error"),
        )

        # CSV backup via logger service
        try:
            from services.logger import log_application as csv_log
            csv_log(
                platform=job.get("source", "unknown"),
                title=job.get("role", ""),
                company=job.get("company", ""),
                location=job.get("location", ""),
                url=url,
                status=result["status"],
            )
        except Exception:
            pass  # CSV backup is optional

        # Update counters
        self._applied_urls.add(url)
        self._platform_counts[method] = self._platform_counts.get(method, 0) + 1

        with _apply_lock:
            p = auto_apply_state["progress"]
            p["total_attempted"] += 1
            if result["status"] == "applied":
                p["applied"] += 1
            elif result["status"] == "failed":
                p["failed"] += 1
            else:
                p["skipped"] += 1

        _emit({
            "type": result["status"],
            "job": job.get("role", "")[:30],
            "company": job.get("company", "")[:25],
            "method": result["method"],
            "tier": tier_label,
            "error": result.get("error", ""),
        })

        # Rate limiting — premium tier gets longer delays (more human-like)
        if tier_label == "PREMIUM":
            time.sleep(random.uniform(60, 150))
        else:
            limits = RATE_LIMITS.get(method, RATE_LIMITS["default"])
            time.sleep(random.uniform(*limits))

        return result

    def run(self, max_applications: int = 500, on_complete=None):
        """Run the auto-apply cycle. Processes jobs until quota or max reached."""
        with _apply_lock:
            auto_apply_state["running"] = True
            auto_apply_state["status"] = "running"
            auto_apply_state["started_at"] = datetime.now().isoformat()
            auto_apply_state["progress"] = {
                "total_attempted": 0, "applied": 0, "failed": 0, "skipped": 0, "current_job": None,
            }
            auto_apply_state["log"] = []

        _stop_flag.clear()
        _emit({"type": "info", "message": f"Starting auto-apply cycle (target: {max_applications})"})

        try:
            jobs = get_unapplied_jobs(self.conn, limit=max_applications * 2)
            _emit({"type": "info", "message": f"Found {len(jobs)} unapplied jobs in queue"})

            applied_count = 0
            for job in jobs:
                if _stop_flag.is_set():
                    _emit({"type": "info", "message": "Auto-apply stopped by user"})
                    break

                if applied_count >= max_applications:
                    _emit({"type": "info", "message": f"Reached target of {max_applications} applications"})
                    break

                if quota_remaining(self.conn) <= 0:
                    _emit({"type": "info", "message": "Daily quota exhausted"})
                    break

                should, reason = self.should_apply(job)
                if not should:
                    continue

                result = self.apply_one(job)
                if result["status"] == "applied":
                    applied_count += 1

        except Exception as e:
            _emit({"type": "error", "message": f"Auto-apply error: {str(e)[:300]}"})
            with _apply_lock:
                auto_apply_state["status"] = "error"
        finally:
            with _apply_lock:
                if auto_apply_state["status"] == "running":
                    auto_apply_state["status"] = "done"
                auto_apply_state["running"] = False
                auto_apply_state["progress"]["current_job"] = None

            _emit({"type": "done", "message": f"Auto-apply complete: {auto_apply_state['progress']}"})

            if on_complete:
                on_complete(auto_apply_state["progress"])


def submit_review(decision: str) -> dict:
    """User's decision on the application waiting for review: 'submit' or 'skip'."""
    if decision not in ("submit", "skip"):
        return {"status": "error", "message": "decision must be 'submit' or 'skip'"}
    with _apply_lock:
        if not auto_apply_state["pending_review"]:
            return {"status": "error", "message": "Nothing is waiting for review"}
    _review_decision["decision"] = decision
    _review_event.set()
    return {"status": "ok", "decision": decision}


def start_auto_apply(max_applications: int = 500, user_id=None, review: bool = True):
    """Start auto-apply in a background thread."""
    with _apply_lock:
        if auto_apply_state["running"]:
            return {"error": "Auto-apply already running"}
        auto_apply_state["running"] = True
        auto_apply_state["review"] = review

    from services.browser_service import browser_state
    from worker_ctx import run_with_user

    page = browser_state.get("page")

    def _auto_apply_thread():
        conn = init_db()  # resolves the triggering user's DB (context set below)
        engine = AutoApplyEngine(conn, page=page)
        try:
            engine.run(max_applications)
        finally:
            conn.close()

    t = threading.Thread(
        target=run_with_user(user_id, _auto_apply_thread),
        daemon=True,
    )
    t.start()
    return {"status": "started", "target": max_applications}


def stop_auto_apply():
    """Signal the auto-apply loop to stop."""
    _stop_flag.set()
    return {"status": "stopping"}


def get_auto_apply_status() -> dict:
    """Get current auto-apply status."""
    with _apply_lock:
        return {
            "running": auto_apply_state["running"],
            "status": auto_apply_state["status"],
            "started_at": auto_apply_state["started_at"],
            "progress": auto_apply_state["progress"].copy(),
            "review": auto_apply_state["review"],
            "pending_review": auto_apply_state["pending_review"],
            "log": auto_apply_state["log"][-100:],
        }
