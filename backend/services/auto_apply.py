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
    "linkedin_easy_apply": 120,
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
}

_apply_lock = threading.Lock()
_stop_flag = threading.Event()


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


def _linkedin_easy_apply(page, job: dict) -> dict:
    """Automate LinkedIn Easy Apply flow via Playwright.
    Returns {"status": "applied"|"failed", "method": "easy_apply", "error": ...}
    """
    url = job.get("apply_url") or job.get("post_url", "")
    if not url or "linkedin.com" not in url:
        return {"status": "failed", "method": "easy_apply", "error": "Not a LinkedIn URL"}

    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        time.sleep(random.uniform(2, 4))

        # Warm-up: simulate reading the job description before applying
        _linkedin_warm_up(page, job)

        # Look for Easy Apply button
        easy_apply_btn = page.query_selector('button[aria-label*="Easy Apply"], button.jobs-apply-button')
        if not easy_apply_btn:
            return {"status": "failed", "method": "easy_apply", "error": "No Easy Apply button found"}

        easy_apply_btn.click()
        time.sleep(random.uniform(2, 3))

        # Handle multi-step form
        max_steps = 8
        for step in range(max_steps):
            # Fill common fields (with job context for smart answers)
            _fill_form_fields(page, job_context=job)
            time.sleep(random.uniform(1, 2))

            # Check for submit button
            submit_btn = page.query_selector(
                'button[aria-label*="Submit application"], '
                'button[aria-label*="Submit"], '
                'button[data-easy-apply-next-button]:has-text("Submit")'
            )
            if submit_btn:
                submit_btn.click()
                time.sleep(random.uniform(2, 3))

                # Check for success
                success = page.query_selector(
                    '[data-test-modal-close-btn], '
                    'h2:has-text("applied"), '
                    '[aria-label*="Dismiss"], '
                    'button:has-text("Done")'
                )
                if success:
                    # Close the confirmation dialog
                    try:
                        success.click()
                    except Exception:
                        pass
                    return {"status": "applied", "method": "easy_apply"}
                return {"status": "applied", "method": "easy_apply"}

            # Click Next button for multi-step forms
            next_btn = page.query_selector(
                'button[aria-label*="Continue"], '
                'button[aria-label*="Next"], '
                'button[data-easy-apply-next-button], '
                'button:has-text("Next"), '
                'button:has-text("Review")'
            )
            if next_btn:
                next_btn.click()
                time.sleep(random.uniform(1.5, 2.5))
            else:
                break

        return {"status": "failed", "method": "easy_apply", "error": "Could not complete form steps"}

    except Exception as e:
        return {"status": "failed", "method": "easy_apply", "error": str(e)[:200]}


def _fill_form_fields(page, job_context: dict = None):
    """Fill common Easy Apply form fields from PROFILE config."""
    # Store job context for sub-functions
    _fill_form_fields._job_context = job_context or {}
    field_map = {
        'input[name*="phone"], input[aria-label*="phone"], input[id*="phone"]': PROFILE.get("phone", ""),
        'input[name*="city"], input[aria-label*="city"], input[id*="city"]': PROFILE.get("location", "India"),
    }

    for selector, value in field_map.items():
        if not value:
            continue
        try:
            field = page.query_selector(selector)
            if field:
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
                resume_path = Path(PROFILE.get("resume_path", "assets/resumes/default/vineet_kukreti_resume.pdf"))
            if resume_path.exists():
                upload.set_input_files(str(resume_path))
    except Exception:
        pass

    # Handle text areas and custom questions (LLM-powered)
    _handle_text_questions(page, job_context=getattr(_fill_form_fields, '_job_context', {}))

    # Handle select dropdowns (experience, education, etc.)
    _handle_dropdowns(page)

    # Handle yes/no radio buttons (work authorization, sponsorship, etc.)
    _handle_radio_buttons(page)

    # Handle numeric input fields (salary, years, etc.)
    _handle_numeric_inputs(page)


def _handle_text_questions(page, job_context: dict = None):
    """Fill text areas and custom text inputs using known answers + LLM.
    LLM is only used for premium tier jobs (job._use_llm=True).
    """
    use_llm = (job_context or {}).get("_use_llm", False)
    try:
        textareas = page.query_selector_all('textarea')
        for ta in textareas:
            current = ta.input_value()
            if current:  # Already filled
                continue

            # Get the question label
            question = _get_field_label(page, ta)
            if not question:
                continue

            # Try known answer first (free), then LLM if tier allows
            answer = _get_known_answer(question.lower().strip())
            if not answer and use_llm:
                answer = _llm_answer_question(question, job_context)
            if answer:
                ta.fill(answer)
                time.sleep(random.uniform(0.3, 0.8))

        # Also handle text inputs that look like custom questions
        # (not phone, city, email, name — those are handled elsewhere)
        skip_patterns = ["phone", "city", "email", "name", "first", "last",
                         "zip", "postal", "address", "url", "linkedin", "github",
                         "website", "search"]
        inputs = page.query_selector_all('input[type="text"]')
        for inp in inputs:
            current = inp.input_value()
            if current:
                continue
            label = _get_field_label(page, inp)
            if not label:
                continue
            label_lower = label.lower()
            if any(skip in label_lower for skip in skip_patterns):
                continue
            # Likely a custom question — answer it
            answer = _answer_form_question(label, job_context)
            if answer:
                # Text inputs need shorter answers
                inp.fill(answer[:200])
                time.sleep(random.uniform(0.2, 0.5))
    except Exception:
        pass


def _handle_numeric_inputs(page):
    """Fill numeric input fields (salary expectation, notice period, etc.)."""
    try:
        inputs = page.query_selector_all('input[type="number"]')
        for inp in inputs:
            current = inp.input_value()
            if current:
                continue
            label = _get_field_label(page, inp)
            if not label:
                continue
            label_lower = label.lower()

            if any(kw in label_lower for kw in ["salary", "compensation", "pay", "ctc"]):
                inp.fill(str(PROFILE.get("desired_salary", 1200000)))
            elif any(kw in label_lower for kw in ["notice", "days"]):
                inp.fill(str(PROFILE.get("notice_period_days", 30)))
            elif any(kw in label_lower for kw in ["experience", "years"]):
                inp.fill(str(PROFILE.get("experience_years", 2)))
            elif any(kw in label_lower for kw in ["gpa", "cgpa", "grade"]):
                inp.fill("8")
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


def _answer_form_question(question: str, job_context: dict = None) -> str:
    """Generate an answer for a form question. Uses cache + known answers + LLM fallback."""
    if not question:
        return ""

    question_lower = question.lower().strip()

    # Check cache first
    cache_key = question_lower[:80]
    if cache_key in _answer_cache:
        return _answer_cache[cache_key]

    # Known answers (no LLM needed)
    answer = _get_known_answer(question_lower)
    if answer:
        _answer_cache[cache_key] = answer
        return answer

    # LLM-generated answer
    answer = _llm_answer_question(question, job_context)
    if answer:
        _answer_cache[cache_key] = answer
    return answer


def _get_known_answer(question_lower: str) -> str:
    """Return known answers for common form questions without calling LLM."""
    name = PROFILE["name"]
    exp = PROFILE.get("experience_years", 2)

    # Salary / compensation
    if any(kw in question_lower for kw in ["salary", "compensation", "expected ctc", "pay expectation"]):
        return str(PROFILE.get("desired_salary", 1200000))

    # Notice period
    if any(kw in question_lower for kw in ["notice period", "days to join", "when can you start"]):
        return f"{PROFILE.get('notice_period_days', 30)} days"

    # Years of experience
    if any(kw in question_lower for kw in ["years of experience", "total experience", "how many years"]):
        return str(exp)

    # Work authorization
    if any(kw in question_lower for kw in ["authorized to work", "work authorization", "legally authorized"]):
        return "Yes"

    # Sponsorship
    if any(kw in question_lower for kw in ["sponsorship", "require visa", "need visa"]):
        return "No"

    # Relocation
    if any(kw in question_lower for kw in ["willing to relocate", "open to relocation"]):
        return "Yes"

    # LinkedIn
    if "linkedin" in question_lower:
        return PROFILE.get("linkedin", "")

    # GitHub / portfolio
    if any(kw in question_lower for kw in ["github", "portfolio", "personal website"]):
        return PROFILE.get("github", "")

    # How did you hear
    if any(kw in question_lower for kw in ["how did you hear", "where did you find", "how did you learn"]):
        return "LinkedIn"

    # Current company
    if any(kw in question_lower for kw in ["current company", "current employer", "present company"]):
        return "Healthcare AI startup (US medical domain)"

    # Current title
    if any(kw in question_lower for kw in ["current title", "current role", "job title"]):
        return PROFILE.get("current_title", "AI Engineer")

    # Education
    if any(kw in question_lower for kw in ["highest education", "degree", "qualification"]):
        return PROFILE.get("education_level", "Bachelor's Degree")

    # Gender / diversity (decline)
    if any(kw in question_lower for kw in ["gender", "ethnicity", "race", "disability", "veteran"]):
        return "Decline to self-identify"

    return ""


def _llm_answer_question(question: str, job_context: dict = None) -> str:
    """Use Gemini to answer a custom form question based on profile + job context."""
    try:
        from services.ai_tools import _call_gemini

        role = (job_context or {}).get("role", "AI/ML role")
        company = (job_context or {}).get("company", "the company")
        content = (job_context or {}).get("content", "")[:500]

        prompt = f"""Answer this job application form question concisely (2-4 sentences max).

QUESTION: {question}

CANDIDATE: Vineet Kukreti, AI Engineer, {PROFILE.get('experience_years', 2)} years exp at Southguild Technologies.
Building production healthcare AI platforms across dermatopathology and oncology.
Skills: Python, FastAPI, Neo4j, LLMs (Claude/OpenAI/Cohere), knowledge graphs, Docker.
Key projects: PathAssist (98.8% accuracy NLP-to-Cypher retrieval), Target Discovery ETL (100K+ records), Navya Oncology Pipeline (80% less manual work).
Achievements: 3 patents, 2 IEEE papers, PMSS scholar.

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
        if answer and len(answer) > 10:
            return answer

    except Exception:
        pass
    return ""


def _handle_dropdowns(page):
    """Handle select/dropdown fields in Easy Apply forms."""
    try:
        selects = page.query_selector_all('select')
        for select in selects:
            label = select.get_attribute("aria-label") or ""
            label_lower = label.lower()

            if any(kw in label_lower for kw in ["experience", "years"]):
                # Select the closest match to our experience
                options = select.query_selector_all('option')
                for opt in options:
                    text = opt.inner_text().lower()
                    if "2" in text or "1-3" in text or "1" in text:
                        select.select_option(value=opt.get_attribute("value"))
                        break

            elif any(kw in label_lower for kw in ["education", "degree"]):
                options = select.query_selector_all('option')
                for opt in options:
                    text = opt.inner_text().lower()
                    if "bachelor" in text:
                        select.select_option(value=opt.get_attribute("value"))
                        break
    except Exception:
        pass


def _handle_radio_buttons(page):
    """Handle yes/no radio buttons (work authorization, relocate, etc.)."""
    try:
        fieldsets = page.query_selector_all('fieldset')
        for fs in fieldsets:
            legend = fs.query_selector('legend, label, span')
            if not legend:
                continue
            text = legend.inner_text().lower()

            # Default to "Yes" for most questions (willing to relocate, authorized, etc.)
            if any(kw in text for kw in ["authorized", "relocate", "willing", "eligible", "legally"]):
                yes_radio = fs.query_selector('input[value="Yes"], input[value="yes"], label:has-text("Yes") input')
                if yes_radio:
                    yes_radio.click()

            # Default to "No" for sponsorship questions
            elif any(kw in text for kw in ["sponsor", "visa"]):
                no_radio = fs.query_selector('input[value="No"], input[value="no"], label:has-text("No") input')
                if no_radio:
                    no_radio.click()
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

    body = f"""Hi,

I'm {name}, an AI Engineer with {PROFILE.get('experience_years', 2)} years of experience building production AI/ML systems. I'm writing to express my interest in the {role} position at {company}.

Currently, I'm working in the US healthcare domain, building fax automation systems for hospitals — solving real workflow problems with LLM-based systems, RAG pipelines, and API integrations.

Key highlights:
- Production experience with LLMs, RAG, and multi-agent AI systems
- Strong Python background (FastAPI, PyTorch, LangChain, Neo4j)
- Healthcare AI domain expertise with compliance requirements
- Built knowledge graph systems and ETL pipelines at scale

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
        if is_live is not None and is_live == 0:
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
            result = _linkedin_easy_apply(self.page, job)
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


def start_auto_apply(max_applications: int = 500):
    """Start auto-apply in a background thread."""
    with _apply_lock:
        if auto_apply_state["running"]:
            return {"error": "Auto-apply already running"}
        auto_apply_state["running"] = True

    from services.browser_service import browser_state

    page = browser_state.get("page")

    def _auto_apply_thread():
        conn = init_db()
        engine = AutoApplyEngine(conn, page=page)
        try:
            engine.run(max_applications)
        finally:
            conn.close()

    t = threading.Thread(
        target=_auto_apply_thread,
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
            "log": auto_apply_state["log"][-100:],
        }
