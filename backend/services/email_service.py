"""Email service — generation, sending, and bulk worker operations."""

import os
import random
import re
import smtplib
import time
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path

import requests
from dotenv import load_dotenv

from config import PROFILE, RESUME_SKILLS
from db import init_db

load_dotenv()

# ───────────────────────────────────────────────
# SMTP / Email config
# ───────────────────────────────────────────────

SMTP_CONFIG = {
    "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
    "port": int(os.getenv("SMTP_PORT", "587")),
    "user": os.getenv("SMTP_USER", ""),
    "password": os.getenv("SMTP_PASSWORD", ""),
    "from_email": os.getenv("FROM_EMAIL", ""),
    "from_name": os.getenv("FROM_NAME", "Vineet Kukreti"),
}

# ───────────────────────────────────────────────
# Email blocklist (never send outreach to these)
# ───────────────────────────────────────────────

EMAIL_BLOCKLIST = ["southguild"]  # current employer — never send outreach here


def _is_blocked_email(email: str, company: str = "") -> bool:
    """Check if email or company matches blocklist (current employer, etc)."""
    check = f"{email} {company}".lower()
    return any(b in check for b in EMAIL_BLOCKLIST)


# ───────────────────────────────────────────────
# Email generation agent (Gemini 2.5 Flash Lite)
# ───────────────────────────────────────────────

EMAIL_AGENT_PROMPT = """You are an AI job outreach assistant specialized in generating highly personalized, human-like recruiter emails for AI/ML/Data roles.

Your goal is to maximize recruiter response rate.

You will receive structured data about a hiring post. Some fields may be missing or incomplete. You must intelligently adapt.

━━━ CANDIDATE PROFILE (IMPORTANT CONTEXT) ━━━

Name: Vineet Kukreti
Title: AI Engineer | ~1.5-2 years experience
Location: India
LinkedIn: linkedin.com/in/vineetkukreti
GitHub: github.com/vineetkukreti34

CURRENT ROLE (USE THIS — it shows active, real-world healthcare experience):
- Currently working in the US healthcare/medical domain
- Building fax automation systems for hospitals and patients
- Solving real hospital workflow problems — automating fax-based communication between healthcare providers and patients
- This is production healthcare work with real compliance requirements

Strong experience in:
- RAG pipelines
- LLM-based systems
- ETL pipelines & data workflows
- API integrations
- Healthcare AI systems (currently working in this domain)
- Automation systems

Projects (pick 2-3 that BEST match the target role):
1. Enterprise RAG System — Production RAG pipeline with vector DB (Qdrant), semantic chunking, hybrid search + reranking. Handles 10K+ documents with sub-second retrieval. Focused on improving retrieval quality and reducing response latency.
2. Healthcare AI Pipeline — AI-powered medical pipeline with LLM extraction & knowledge graphs (Neo4j). Processes clinical notes into structured data. HIPAA-aware design.
3. US Healthcare Fax Automation (Current) — Building automation systems for hospital-patient fax workflows. Real production healthcare system handling compliance-sensitive medical communications.
4. Biomedical ETL Platform — Large-scale ETL + biomedical data ingestion from PubMed, clinical trials, FDA databases. Automated pipeline processing 50K+ records/day.
5. Excel Automation Engine — Schema detection + intelligent transformation system. Auto-maps messy spreadsheets to structured DB schemas using LLMs.

━━━ CRITICAL INSTRUCTIONS ━━━

BEFORE writing the email, you MUST:
1. Read the ORIGINAL POST content word by word
2. Identify 2-3 SPECIFIC things they mention (tech stack, problems, domain, what they're building)
3. Map ONLY relevant candidate projects/skills to those SPECIFIC needs
4. Reference something concrete from their post that shows you actually read it — NOT generic "your post caught my eye"

━━━ RULES (STRICT) ━━━

1. Keep email concise (120-180 words max)
2. Tone: Professional, confident, human (NOT robotic)
3. Avoid generic phrases like:
   - "I am very passionate"
   - "I am excited to apply"
   - "I am writing to express my interest..."
   - "Dear Hiring Manager, I hope this email finds you well..."
   - "caught my eye" / "resonated with me" / "aligns with my experience" (TOO VAGUE)
4. Personalize based on: role, company, AND specific details from the post content
5. If hiring signal is weak → make it a "value + interest" outreach
6. If email is missing → still generate email content (assume user will find it)
7. If role/company missing → infer from content or keep neutral
8. Always highlight RELEVANT experience only — match to what THEY asked for
9. Do NOT list everything — pick 2-3 strongest alignments
10. Mention resume naturally ("I've attached my resume for context") — don't describe the attachment
11. NO PLACEHOLDERS: Never use [brackets] or placeholder text. If data is missing, skip it or write around it naturally.
12. Sign off with just "Best,\\nVineet" — not "Best regards, Vineet Kukreti"

━━━ EMAIL STRUCTURE ━━━

1. Opening hook + identity — reference something SPECIFIC from their post AND naturally identify yourself in the same 1-2 sentences. Example: "I'm an AI Engineer currently building healthcare automation systems for the US medical space — your post about the Clinical AI role at Duml Tech maps closely to what I've been working on." Do NOT use a formal intro like "My name is Vineet Kukreti and I am..." — weave who you are into the hook naturally.
2. Context match — 2-3 lines showing what YOU built that solves THEIR specific problem. Use concrete numbers/details (e.g., "processing 50K records/day" not "large-scale systems"). Connect YOUR work to THEIR needs with a clear "you need X → I built X" mapping.
3. Specific value — pick 1 specific problem from their post (e.g., "you mentioned scaling clinical NLP pipelines" or "the part about handling unstructured medical records") and show you've solved it before. Emphasize end-to-end system thinking, not just modeling.
4. Close — polite + confident, one clear low-friction ask. Mention resume attached.
5. Sign off — "Best,\\nVineet"

━━━ ADAPTATION RULES ━━━

IF is_hiring=true AND role+company known:
  → Direct application. Reference the specific role. Match 2 projects to their requirements.

IF is_hiring=true BUT role/company vague:
  → Infer the role from post content. Be specific about what you'd bring.

IF is_hiring=false OR weak signal:
  → Value-first outreach. Lead with curiosity about their work/domain. Position as "interested in what you're building" not "give me a job".

IF healthcare/medical domain:
  → Lead with Healthcare AI Pipeline + Biomedical ETL projects. Mention clinical data experience.

IF general AI/ML role:
  → Lead with Enterprise RAG + LLM experience. Mention production-scale systems.

IF data engineering role:
  → Lead with Biomedical ETL + Excel Automation. Mention pipeline scale + automation.

━━━ OUTPUT FORMAT (EXACT) ━━━

Return ONLY this, nothing else:

Subject: <clear, role-focused subject line>

<email body starting directly with "Hi {author_first_name}," then the hook — no "Email:" label>

━━━ STYLE EXAMPLES ━━━

GOOD opening:
"Saw your post about hiring for ML roles — this aligns closely with the kind of systems I've been building recently."
"Came across your post about the Data Engineer role at Acme — this is exactly the kind of problem space I've been working in."

BAD opening (NEVER do this):
"I am writing to express my keen interest in the position..."
"Dear Hiring Manager, I hope this email finds you well..."
"As a highly motivated AI professional with a passion for..."

━━━ EDGE CASE HANDLING ━━━

- Missing company → skip or generalize naturally
- Missing role → infer from keywords in post content
- No hiring signal → make it curiosity + value outreach
- Weak content → focus on domain relevance
"""


def _build_email_input(post_data: dict) -> str:
    """Build the input data block for the email agent."""
    parts = []
    if post_data.get("author_name"):
        parts.append(f"Posted by: {post_data['author_name']}")
    if post_data.get("author_headline"):
        parts.append(f"Their title: {post_data['author_headline']}")
    if post_data.get("role"):
        parts.append(f"Role hiring for: {post_data['role']}")
    if post_data.get("company"):
        parts.append(f"Company: {post_data['company']}")
    if post_data.get("location"):
        parts.append(f"Location: {post_data['location']}")
    if post_data.get("experience"):
        parts.append(f"Experience required: {post_data['experience']}")
    parts.append(f"Hiring signal: {'Strong' if post_data.get('is_hiring') else 'Weak/Unclear'}")
    if post_data.get("domain_relevance"):
        parts.append(f"Healthcare domain relevance: {post_data['domain_relevance']}")
    if post_data.get("links"):
        parts.append(f"Links in post: {post_data['links']}")
    if post_data.get("post_url"):
        parts.append(f"Post URL: {post_data['post_url']}")
    if post_data.get("author_profile"):
        parts.append(f"Author LinkedIn: {post_data['author_profile']}")
    content = (post_data.get("content") or "")[:1500].strip()
    if content:
        parts.append(f'\nOriginal post (READ THIS CAREFULLY — extract specific details to personalize the email):\n"""\n{content}\n"""')
    return "\n".join(parts)


def _generate_email_with_gemini(post_data: dict) -> dict:
    """Generate personalized cold email using Gemini 2.5 Flash Lite (cheapest)."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env")

    input_block = _build_email_input(post_data)
    prompt = f"{EMAIL_AGENT_PROMPT}\n\n━━━ INPUT DATA FOR THIS EMAIL ━━━\n\n{input_block}\n\nGenerate the email now."

    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}",
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 400,
                "topP": 0.9,
            },
        },
        timeout=30,
    )
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]

    return _parse_generated_email(text, post_data)


def _generate_email_with_ollama(post_data: dict) -> dict:
    """Generate email using local Ollama, fallback to Gemini."""
    input_block = _build_email_input(post_data)
    prompt = f"{EMAIL_AGENT_PROMPT}\n\n━━━ INPUT DATA FOR THIS EMAIL ━━━\n\n{input_block}\n\nGenerate the email now."

    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "qwen2.5:7b", "prompt": prompt, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        text = resp.json().get("response", "")
    except Exception:
        return _generate_email_with_gemini(post_data)

    return _parse_generated_email(text, post_data)


def _parse_generated_email(text: str, post_data: dict) -> dict:
    """Parse AI-generated email into subject + body. Handles multiple output formats."""
    text = text.strip().strip("```").strip()
    subject = ""
    body = text

    if "Subject:" in text:
        lines = text.split("\n")
        # Find the Subject: line
        subject_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("Subject:"):
                subject = line.strip().replace("Subject:", "").strip().strip('"')
                subject_idx = i
                break

        if subject_idx >= 0:
            # Everything after the subject line is the body
            remaining = lines[subject_idx + 1:]
            # Skip any "Email:" label line and blank lines at the start
            while remaining and (not remaining[0].strip() or remaining[0].strip().lower() in ("email:", "body:")):
                remaining.pop(0)
            body = "\n".join(remaining).strip()

        # Remove any duplicate Subject: lines that leaked into body
        body_lines = body.split("\n")
        body_lines = [l for l in body_lines if not l.strip().startswith("Subject:")]
        body = "\n".join(body_lines).strip()

    # Safety: catch any remaining [placeholder] brackets the model ignored
    author = post_data.get("author_name", "").strip()
    first_name = author.split()[0] if author else "Hi"
    company = post_data.get("company", "").strip()
    role = post_data.get("role", "").strip()

    bracket_replacements = {
        "[Recruiter Name]": first_name,
        "[Hiring Manager Name]": first_name,
        "[Hiring Manager]": first_name,
        "[Your Name]": "Vineet",
        "[Name]": first_name,
        "[Company]": company or "your team",
        "[Role]": role or "the role",
        "[company]": company or "your team",
        "[role]": role or "the role",
    }
    for placeholder, value in bracket_replacements.items():
        subject = subject.replace(placeholder, value)
        body = body.replace(placeholder, value)

    # Strip trailing signature duplicates
    body = body.rstrip()
    if body.endswith("Vineet Kukreti"):
        body = body[:-len("Vineet Kukreti")].rstrip().rstrip(",").rstrip()
        body += "\nVineet"

    return {"subject": subject, "body": body}


def _send_email_smtp(to_email: str, subject: str, body: str, attach_resume: bool = False) -> dict:
    """Send email via SMTP (Gmail). Optionally attach resume PDF."""
    cfg = SMTP_CONFIG
    if not cfg["password"]:
        raise ValueError("SMTP_PASSWORD not set in .env. Generate a Gmail App Password first.")

    msg = MIMEMultipart("mixed")
    msg["From"] = f"{cfg['from_name']} <{cfg['from_email']}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    # Text content as a sub-part
    text_part = MIMEMultipart("alternative")
    text_part.attach(MIMEText(body, "plain"))

    # Simple HTML version (preserves line breaks)
    html_body = body.replace("\n", "<br>")
    html = f"""<html><body style="font-family: Arial, sans-serif; font-size: 14px; color: #333; line-height: 1.6;">
{html_body}
<br><br>
<span style="color: #666; font-size: 12px;">—<br>{cfg['from_name']}<br>{PROFILE.get('current_title', 'AI Engineer')}<br>{PROFILE.get('linkedin', '')}</span>
</body></html>"""
    text_part.attach(MIMEText(html, "html"))
    msg.attach(text_part)

    # Attach resume PDF if requested
    if attach_resume:
        resume_path = Path(PROFILE.get("resume_path", ""))
        if resume_path.exists():
            with open(resume_path, "rb") as f:
                pdf = MIMEApplication(f.read(), _subtype="pdf")
                pdf.add_header("Content-Disposition", "attachment", filename=resume_path.name)
                msg.attach(pdf)

    with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
        server.starttls()
        server.login(cfg["user"], cfg["password"])
        server.send_message(msg)

    return {"status": "sent", "to": to_email, "subject": subject}


def send_email_with_resume(to_email: str, subject: str, body: str, resume_path: str = "") -> dict:
    """Public wrapper: send an email with resume attached.
    Returns {"success": True/False, "error": ...}
    """
    try:
        _send_email_smtp(to_email, subject, body, attach_resume=True)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)[:300]}


# ───────────────────────────────────────────────
# Background email workers (non-blocking)
# ───────────────────────────────────────────────

_email_lock = threading.Lock()

email_worker_state = {
    "running": False,
    "task": None,       # "generating" | "sending"
    "current": 0,
    "total": 0,
    "current_label": "",
    "results": [],      # list of {post_id, status, message, ...}
    "error": None,
}


def _bulk_generate_worker(post_ids: list[int]):
    """Background thread: generate emails for given post IDs."""
    conn = init_db()
    with _email_lock:
        email_worker_state["running"] = True
        email_worker_state["task"] = "generating"
        email_worker_state["total"] = len(post_ids)
        email_worker_state["current"] = 0
        email_worker_state["results"] = []
        email_worker_state["error"] = None

    for i, post_id in enumerate(post_ids):
        with _email_lock:
            if not email_worker_state["running"]:
                break
            email_worker_state["current"] = i + 1

        row = conn.execute(
            """SELECT p.id, p.author_name, p.author_headline, p.content, p.email,
                      p.links, p.domain_relevance, p.is_hiring, p.post_url,
                      j.role, j.company, j.location, j.experience
               FROM posts p LEFT JOIN jobs j ON j.post_id = p.id
               WHERE p.id = ?""",
            (post_id,),
        ).fetchone()
        if not row:
            with _email_lock:
                email_worker_state["results"].append({"post_id": post_id, "status": "error", "message": "Post not found"})
            continue

        row = dict(row)

        # Skip blocked emails (current employer, etc)
        if _is_blocked_email(row.get("email", ""), row.get("company", "")):
            with _email_lock:
                email_worker_state["results"].append({"post_id": post_id, "status": "skipped", "message": "Blocked (current employer)"})
            continue

        with _email_lock:
            email_worker_state["current_label"] = f"{row.get('author_name', '?')} | {row.get('role', '?')} @ {row.get('company', '?')}"

        try:
            email = _generate_email_with_gemini(row)
            # Save draft to DB
            existing = conn.execute(
                "SELECT id FROM email_outreach WHERE post_id = ? AND status = 'draft'", (post_id,),
            ).fetchone()
            to_email = row.get("email", "")
            if existing:
                conn.execute(
                    "UPDATE email_outreach SET recipient_email=?, subject=?, body=?, created_at=datetime('now') WHERE id=?",
                    (to_email, email["subject"], email["body"], existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO email_outreach (post_id, recipient_email, subject, body, status) VALUES (?, ?, ?, ?, 'draft')",
                    (post_id, to_email, email["subject"], email["body"]),
                )
            conn.commit()
            with _email_lock:
                email_worker_state["results"].append({
                    "post_id": post_id, "status": "ok",
                    "to_email": to_email, "author_name": row.get("author_name", ""),
                    **email,
                })
        except Exception as e:
            with _email_lock:
                email_worker_state["results"].append({"post_id": post_id, "status": "error", "message": str(e)[:200]})

        # Rate limit delay between API calls
        time.sleep(random.uniform(1, 2))

    with _email_lock:
        email_worker_state["running"] = False
        email_worker_state["task"] = None
        email_worker_state["current_label"] = ""


def _bulk_send_worker(attach_resume: bool = True):
    """Background thread: send all draft emails."""
    conn = init_db()
    drafts = conn.execute(
        """SELECT eo.id, eo.post_id, eo.recipient_email, eo.subject, eo.body
           FROM email_outreach eo WHERE eo.status = 'draft' AND eo.subject IS NOT NULL AND eo.body IS NOT NULL"""
    ).fetchall()
    drafts = [dict(r) for r in drafts]

    with _email_lock:
        email_worker_state["running"] = True
        email_worker_state["task"] = "sending"
        email_worker_state["total"] = len(drafts)
        email_worker_state["current"] = 0
        email_worker_state["results"] = []
        email_worker_state["error"] = None

    for i, draft in enumerate(drafts):
        with _email_lock:
            if not email_worker_state["running"]:
                break
            email_worker_state["current"] = i + 1

        # Skip blocked emails (current employer, etc)
        if _is_blocked_email(draft["recipient_email"]):
            with _email_lock:
                email_worker_state["results"].append({"post_id": draft["post_id"], "to": draft["recipient_email"], "status": "skipped", "message": "Blocked (current employer)"})
            continue

        with _email_lock:
            email_worker_state["current_label"] = f"{draft['recipient_email']}"

        try:
            _send_email_smtp(draft["recipient_email"], draft["subject"], draft["body"], attach_resume=attach_resume)
            conn.execute(
                "UPDATE email_outreach SET status='sent', sent_at=datetime('now') WHERE id=?",
                (draft["id"],),
            )
            conn.commit()
            with _email_lock:
                email_worker_state["results"].append({"post_id": draft["post_id"], "to": draft["recipient_email"], "status": "sent"})
        except Exception as e:
            conn.execute("UPDATE email_outreach SET status='failed' WHERE id=?", (draft["id"],))
            conn.commit()
            with _email_lock:
                email_worker_state["results"].append({"post_id": draft["post_id"], "to": draft["recipient_email"], "status": "failed", "error": str(e)[:200]})

        # Anti-spam delay
        time.sleep(random.uniform(3, 8))

    with _email_lock:
        email_worker_state["running"] = False
        email_worker_state["task"] = None
        email_worker_state["current_label"] = ""
