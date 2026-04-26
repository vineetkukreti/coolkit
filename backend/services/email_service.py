"""Email service — generation, sending, and bulk worker operations."""

import json
import os
import random
import re
import smtplib
import socket
import time
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path

import requests
from dotenv import load_dotenv

import dns.resolver

from config import PROFILE, RESUME_SKILLS
from db import init_db
from services.email_ab_test import pick_variant, record_variant
from services.referral_detector import find_connections
from services.followup_cadence import analyze_followups, record_followup

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

EMAIL_BLOCKLIST = [
    "southguild",          # current employer
    "lnkd.in",            # LinkedIn shortened URLs (not real emails)
    "hubs.li",            # HubSpot tracking URLs (not real emails)
    "oscarhealth.com",    # rejects external email
    "komodohealth.com",   # rejects external email
    "hingehealth.com",    # rejects external email
    "radformation.com",   # bounces
    "capgemini.com",      # rejects external email
    "cognizant.com",      # rejects external email
    "reed.co.uk",         # bounces (malformed addresses like .reed@)
    "reedglobal.com",     # bounces
    "synextra.co.uk",     # bounces
    "captionhealth.com",  # bounces
    "nimblercm.com",      # bounces
]


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
Title: AI Engineer | 2 years experience
Location: India (Coimbatore)
LinkedIn: linkedin.com/in/vineetkukreti
GitHub: github.com/vineetkukreti

CURRENT ROLE:
- AI Engineer at Southguild Technologies (May 2024 – Present)
- Building production-grade healthcare AI platforms across dermatopathology and oncology
- Supporting real-world clinical and biomedical research workflows

Strong experience in:
- Knowledge Graphs (Neo4j) & NLP-to-Cypher pipelines
- LLM-driven systems (Cohere, Claude, OpenAI)
- ETL pipelines for biomedical data
- FastAPI microservices & Docker deployment
- Healthcare AI (dermatopathology, oncology)

Projects (pick 2-3 that BEST match the target role):
1. PathAssist: Dermatopathology Retrieval System — End-to-end clinician-validated retrieval system using Neo4j knowledge graphs. NLP-to-Cypher pipeline achieving 98.8% accuracy (88/89), 5x faster clinical insight retrieval, 60% reduction in clinician research time. Validated by clinicians, presented at medical conference.
2. Target Discovery ETL Pipeline — Unified ETL pipeline integrating heterogeneous biomedical databases for gastric cancer drug-target discovery. Modeled gene-protein-pathway-mutation interactions. Graph analytics over 100K+ records, 65% improvement in biomedical data accessibility.
3. Navya Medical AI Pipeline — LLM-assisted oncology data pipeline for automated patient data extraction and classification. Reduced manual processing by 80%, improved data consistency across clinical datasets.

ACHIEVEMENTS:
- 3 patents in AI/ML applications
- 2 research papers published at IEEE International Conferences
- PMSS Scholarship (Prime Minister's Scholarship Scheme)
- B.Tech (Hons.) in CS Engineering, 8.5 CGPA, ML & AI specialization

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

    if post_data.get("variant_instruction"):
        prompt += f"\n\nSTRATEGY: {post_data['variant_instruction']}"

    if post_data.get("referral_context"):
        ctx = post_data["referral_context"]
        contact = ctx["contacts"][0] if ctx.get("contacts") else None
        if contact:
            prompt += f"\n\nCONNECTION AT COMPANY: You know {contact.get('name', 'someone')} ({contact.get('headline', '')}) at this company. {contact.get('detail', '')}. Reference this connection naturally to establish warmth — don't be creepy, just mention it briefly."

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
        "[Author Name]": first_name,
        "[Author name]": first_name,
        "[author name]": first_name,
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

    # Catch-all: replace any remaining [brackets] the dict missed
    subject = re.sub(r'\[([^\]]+)\]', '', subject)
    body = re.sub(r'\[([^\]]+)\]', lambda m: first_name if 'name' in m.group(1).lower() else '', body)

    # Strip trailing signature duplicates
    body = body.rstrip()
    if body.endswith("Vineet Kukreti"):
        body = body[:-len("Vineet Kukreti")].rstrip().rstrip(",").rstrip()
        body += "\nVineet"

    return {"subject": subject, "body": body}


def validate_email_before_send(email: str) -> dict:
    """Quick validation: format + MX records. Returns {valid, reason}."""
    if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return {"valid": False, "reason": f"Malformed email address: {email}"}
    domain = email.split("@")[1]
    try:
        dns.resolver.resolve(domain, "MX", lifetime=5)
    except Exception:
        return {"valid": False, "reason": f"Domain '{domain}' has no mail server (MX records not found)"}
    return {"valid": True, "reason": "ok"}


def _send_email_smtp(to_email: str, subject: str, body: str, attach_resume: bool = False) -> dict:
    """Send email via SMTP (Gmail). Optionally attach resume PDF."""
    # Handle comma-separated addresses — send to first valid one
    if "," in to_email:
        addresses = [a.strip() for a in to_email.split(",") if a.strip()]
        to_email = addresses[0]  # Use first address as primary recipient

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

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.send_message(msg)
        return {"status": "sent", "to": to_email, "subject": subject}
    except smtplib.SMTPRecipientsRefused as e:
        return {"status": "failed", "to": to_email, "error_type": "invalid_address", "error_message": f"Recipient refused: {e}"}
    except smtplib.SMTPAuthenticationError as e:
        return {"status": "failed", "to": to_email, "error_type": "auth_error", "error_message": f"Auth failed: {e}"}
    except smtplib.SMTPServerDisconnected as e:
        return {"status": "failed", "to": to_email, "error_type": "connection", "error_message": f"Server disconnected: {e}"}
    except smtplib.SMTPResponseException as e:
        return {"status": "failed", "to": to_email, "error_type": "rejected", "error_message": f"SMTP error {e.smtp_code}: {e.smtp_error}"}
    except (socket.timeout, TimeoutError) as e:
        return {"status": "failed", "to": to_email, "error_type": "timeout", "error_message": f"Timeout: {e}"}
    except Exception as e:
        return {"status": "failed", "to": to_email, "error_type": "unknown", "error_message": str(e)[:500]}


def send_email_with_resume(to_email: str, subject: str, body: str, resume_path: str = "") -> dict:
    """Public wrapper: send an email with resume attached.
    Returns {"success": True/False, "error": ...}
    """
    check = validate_email_before_send(to_email)
    if not check["valid"]:
        return {"success": False, "error": check["reason"]}
    try:
        result = _send_email_smtp(to_email, subject, body, attach_resume=True)
        if result["status"] == "sent":
            return {"success": True}
        return {"success": False, "error": result.get("error_message", "Send failed")[:300]}
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
    run_id = conn.execute(
        "INSERT INTO worker_runs (worker_type, total) VALUES (?, ?)",
        ("bulk_generate", len(post_ids))
    ).lastrowid
    conn.commit()
    succeeded_count = 0
    failed_count = 0
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

        # Pick A/B variant
        variant = pick_variant()
        variant_strategies = {"A": "proof-first: Lead with your strongest quantified achievement, then connect it to their specific need.", "B": "challenge-first: Lead with their specific challenge or pain point, then show how you've solved exactly that."}
        row["variant_instruction"] = variant_strategies.get(variant, "")

        # Check referral connections
        company = row.get("company", "")
        referral_info = None
        outreach_type = "cold"
        if company:
            try:
                referral_info = find_connections(conn, company)
                if referral_info.get("has_connections"):
                    row["referral_context"] = referral_info
                    rec = referral_info.get("recommendation", "cold_apply")
                    if rec in ("warm_followup", "warm_intro"):
                        outreach_type = "warm"
                    elif rec == "referral_outreach":
                        outreach_type = "referral"
            except Exception:
                pass

        to_email = row.get("email", "")
        # Validate email quality
        if to_email and "," in to_email:
            to_email = to_email.split(",")[0].strip()  # Use first address

        validation = validate_email_before_send(to_email)
        if not validation["valid"]:
            with _email_lock:
                email_worker_state["results"].append({"post_id": post_id, "status": "skipped", "message": validation["reason"]})
            failed_count += 1
            continue

        # Dedup: skip if we already emailed this recipient
        existing = conn.execute(
            "SELECT id FROM email_outreach WHERE recipient_email = ? AND status IN ('sent', 'replied', 'draft')",
            (to_email,)
        ).fetchone()
        if existing:
            with _email_lock:
                email_worker_state["results"].append({"post_id": post_id, "status": "skipped", "message": f"Already emailed {to_email}"})
            failed_count += 1
            continue

        # Skip generic addresses (95% bounce rate)
        generic_prefixes = ('info@', 'careers@', 'hr@', 'support@', 'contact@', 'hello@', 'jobs@', 'hiring@', 'team@', 'recruitment@', 'apply@', 'noreply@', 'no-reply@')
        if to_email.lower().startswith(generic_prefixes):
            with _email_lock:
                email_worker_state["results"].append({"post_id": post_id, "status": "skipped", "message": f"Generic address: {to_email}"})
            failed_count += 1
            continue

        try:
            email = _generate_email_with_gemini(row)
            # Save draft to DB
            existing = conn.execute(
                "SELECT id FROM email_outreach WHERE post_id = ? AND status = 'draft'", (post_id,),
            ).fetchone()
            cursor = conn.cursor()
            if existing:
                cursor.execute(
                    "UPDATE email_outreach SET recipient_email=?, subject=?, body=?, created_at=datetime('now') WHERE id=?",
                    (to_email, email["subject"], email["body"], existing["id"]),
                )
                outreach_id = existing["id"]
            else:
                cursor.execute(
                    "INSERT INTO email_outreach (post_id, recipient_email, subject, body, status) VALUES (?, ?, ?, ?, 'draft')",
                    (post_id, to_email, email["subject"], email["body"]),
                )
                outreach_id = cursor.lastrowid
            conn.commit()
            try:
                record_variant(conn, outreach_id, variant, variant_strategies.get(variant, ""))
                cursor.execute("UPDATE email_outreach SET outreach_type = ? WHERE id = ?", (outreach_type, outreach_id))
                conn.commit()
            except Exception:
                pass
            with _email_lock:
                email_worker_state["results"].append({
                    "post_id": post_id, "status": "ok",
                    "to_email": to_email, "author_name": row.get("author_name", ""),
                    **email,
                })
            succeeded_count += 1
        except Exception as e:
            with _email_lock:
                email_worker_state["results"].append({"post_id": post_id, "status": "error", "message": str(e)[:200]})
            failed_count += 1

        # Rate limit delay between API calls
        time.sleep(random.uniform(1, 2))

    conn.execute(
        "UPDATE worker_runs SET finished_at=datetime('now'), status=?, succeeded=?, failed=?, results=? WHERE id=?",
        ("completed", succeeded_count, failed_count, json.dumps(email_worker_state.get("results", [])[-20:]), run_id)
    )
    conn.commit()

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

    run_id = conn.execute(
        "INSERT INTO worker_runs (worker_type, total) VALUES (?, ?)",
        ("bulk_send", len(drafts))
    ).lastrowid
    conn.commit()
    succeeded_count = 0
    failed_count = 0

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

        # Dedup: skip if recipient already has a 'sent' record (different outreach entry)
        already_sent = conn.execute(
            "SELECT id FROM email_outreach WHERE recipient_email = ? AND status = 'sent' AND id != ?",
            (draft["recipient_email"], draft["id"])
        ).fetchone()
        if already_sent:
            with _email_lock:
                email_worker_state["results"].append({"post_id": draft["post_id"], "to": draft["recipient_email"], "status": "skipped", "message": f"Already sent to {draft['recipient_email']}"})
            failed_count += 1
            continue

        with _email_lock:
            email_worker_state["current_label"] = f"{draft['recipient_email']}"

        result = _send_email_smtp(draft["recipient_email"], draft["subject"], draft["body"], attach_resume=attach_resume)
        if result["status"] == "sent":
            conn.execute(
                "UPDATE email_outreach SET status='sent', sent_at=datetime('now') WHERE id=?",
                (draft["id"],),
            )
            conn.commit()
            with _email_lock:
                email_worker_state["results"].append({"post_id": draft["post_id"], "to": draft["recipient_email"], "status": "sent"})
            succeeded_count += 1
        else:
            conn.execute(
                "UPDATE email_outreach SET status='failed', error_message=?, error_type=? WHERE id=?",
                (result.get("error_message", "")[:500], result.get("error_type", "unknown"), draft["id"])
            )
            conn.commit()
            with _email_lock:
                email_worker_state["results"].append({"post_id": draft["post_id"], "to": draft["recipient_email"], "status": "failed", "error": result.get("error_message", "")[:200]})
            failed_count += 1

        # Anti-spam delay
        time.sleep(random.uniform(3, 8))

    conn.execute(
        "UPDATE worker_runs SET finished_at=datetime('now'), status=?, succeeded=?, failed=?, results=? WHERE id=?",
        ("completed", succeeded_count, failed_count, json.dumps(email_worker_state.get("results", [])[-20:]), run_id)
    )
    conn.commit()

    with _email_lock:
        email_worker_state["running"] = False
        email_worker_state["task"] = None
        email_worker_state["current_label"] = ""


# ── Auto Follow-up Worker ──────────────────────────────────────────────────

followup_worker_state = {
    "running": False,
    "current": 0,
    "total": 0,
    "succeeded": 0,
    "failed": 0,
    "results": [],
    "error": None,
}

_followup_lock = threading.Lock()


def _generate_followup_email(conn, outreach_id):
    """Generate a follow-up email for an existing outreach."""
    row = conn.execute(
        "SELECT eo.*, p.content, p.author_name, j.role, j.company "
        "FROM email_outreach eo "
        "LEFT JOIN posts p ON p.id = eo.post_id "
        "LEFT JOIN jobs j ON j.post_id = eo.post_id "
        "WHERE eo.id = ?", (outreach_id,)
    ).fetchone()
    if not row:
        return None

    row = dict(row)
    followup_num = (row.get("followup_count") or 0) + 1
    original_subject = row.get("subject") or "your previous email"
    recipient = row.get("recipient_email")
    company = row.get("company", "the company")
    role = row.get("role", "the role")

    prompt = f"""You are writing follow-up email #{followup_num} for a job application.

ORIGINAL EMAIL SUBJECT: {original_subject}
RECIPIENT: {recipient}
COMPANY: {company}
ROLE: {role}

RULES:
- Keep it SHORT: 60-100 words maximum
- Reference the original email briefly ("Following up on my email about...")
- Add ONE new piece of value (a recent project, a relevant insight, or a specific idea for them)
- Be respectful of their time
- End with a soft call to action
- No "just checking in" or "touching base" — add real value
- Subject line: "Re: {original_subject}" (keep the thread)

OUTPUT FORMAT:
Subject: [subject line]
Body: [email body]
"""

    api_key = os.getenv("GEMINI_API_KEY", "")
    if api_key:
        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 300,
                    },
                },
                timeout=30,
            )
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            result = _parse_generated_email(text, {"author_name": "", "company": company, "role": role})
            if result:
                return result
        except Exception:
            pass

    # Fallback
    return {
        "subject": f"Re: {original_subject}",
        "body": f"Hi,\n\nFollowing up on my previous email about the {role} position at {company}. I'd love to discuss how my experience aligns with what you're building.\n\nBest,\nVineet"
    }


def _auto_followup_worker():
    """Background worker to send follow-ups for all overdue entries."""
    global followup_worker_state
    with _followup_lock:
        if followup_worker_state["running"]:
            return
        followup_worker_state.update(running=True, current=0, total=0, succeeded=0, failed=0, results=[], error=None)

    conn = None
    run_id = None
    try:
        conn = init_db()
        analysis = analyze_followups(conn)
        overdue = [e for e in analysis.get("entries", []) if e.get("urgency") == "overdue"]

        run_id = conn.execute(
            "INSERT INTO worker_runs (worker_type, total) VALUES (?, ?)",
            ("auto_followup", len(overdue))
        ).lastrowid
        conn.commit()

        followup_worker_state["total"] = len(overdue)

        for i, entry in enumerate(overdue):
            if not followup_worker_state["running"]:
                break

            followup_worker_state["current"] = i + 1
            outreach_id = entry["outreach_id"]
            recipient = entry.get("recipient_email", "unknown")

            try:
                email = _generate_followup_email(conn, outreach_id)
                if email:
                    send_result = _send_email_smtp(recipient, email["subject"], email["body"])
                    if send_result["status"] == "sent":
                        record_followup(conn, outreach_id)
                        followup_worker_state["succeeded"] += 1
                        followup_worker_state["results"].append({"email": recipient, "status": "sent"})
                    else:
                        followup_worker_state["failed"] += 1
                        followup_worker_state["results"].append({"email": recipient, "status": "failed", "error": send_result.get("error_message", "Send failed")})
                else:
                    followup_worker_state["failed"] += 1
                    followup_worker_state["results"].append({"email": recipient, "status": "failed", "error": "generation failed"})
            except Exception as e:
                followup_worker_state["failed"] += 1
                followup_worker_state["results"].append({"email": recipient, "status": "failed", "error": str(e)})

            time.sleep(random.uniform(3, 8))

    except Exception as e:
        followup_worker_state["error"] = str(e)
    finally:
        if conn and run_id:
            try:
                conn.execute(
                    "UPDATE worker_runs SET finished_at=datetime('now'), status=?, succeeded=?, failed=?, results=? WHERE id=?",
                    ("completed", followup_worker_state["succeeded"], followup_worker_state["failed"],
                     json.dumps(followup_worker_state.get("results", [])[-20:]), run_id)
                )
                conn.commit()
            except Exception:
                pass
        followup_worker_state["running"] = False


def start_auto_followup():
    """Start the auto-followup worker in a background thread."""
    if followup_worker_state["running"]:
        return {"status": "already_running"}
    t = threading.Thread(target=_auto_followup_worker, daemon=True)
    t.start()
    return {"status": "started", "total": followup_worker_state.get("total", 0)}


def get_followup_worker_status():
    return dict(followup_worker_state)


def stop_followup_worker():
    followup_worker_state["running"] = False
    return {"status": "stopped"}


def preview_followup(outreach_id):
    """Generate a follow-up preview without sending."""
    conn = init_db()
    result = _generate_followup_email(conn, outreach_id)
    return result or {"subject": "", "body": "Could not generate follow-up."}


# ── Reply Classification ──────────────────────────────────────────────────────

def _classify_reply(body: str, subject: str = "") -> str:
    """Classify a reply as: interested, auto_reply, rejection, or info."""
    body_lower = (body or "").lower()
    subject_lower = (subject or "").lower()

    # Auto-reply patterns
    auto_patterns = [
        "we have received your", "ticket has been created", "request received",
        "auto-reply", "automatic reply", "out of office", "ooo",
        "this is an automated", "do not reply", "no-reply",
        "your request", "has been received", "currently experiencing",
        "visit our career site", "apply on our website", "apply online",
    ]
    if any(p in body_lower for p in auto_patterns):
        return "auto_reply"

    # Rejection patterns
    reject_patterns = [
        "not hiring", "position has been filled", "no longer available",
        "looking for more experience", "looking for 3", "looking for 4", "looking for 5",
        "we are looking for", "unfortunately", "not a good fit",
        "not suitable", "overqualified", "underqualified",
        "onsite only", "onsite role", "full time onsite",
        "not the right match", "moved forward with other",
    ]
    if any(p in body_lower for p in reject_patterns):
        return "rejection"

    # Interest patterns
    interest_patterns = [
        "interested", "relevant", "your background", "your experience",
        "would like to", "let's connect", "let's schedule", "let's chat",
        "send your cv", "send cv", "share your resume",
        "open to work", "available", "join", "round",
        "interview", "call", "discussion", "meet",
        "keep you posted", "will reach out", "get back to you",
        "impressive", "great fit", "perfect fit",
    ]
    if any(p in body_lower for p in interest_patterns):
        return "interested"

    return "info"


# ── IMAP Reply Detection Worker ───────────────────────────────────────────────

import imaplib
import email as email_lib
from email.header import decode_header

IMAP_CONFIG = {
    "host": os.getenv("IMAP_HOST", "imap.gmail.com"),
    "port": int(os.getenv("IMAP_PORT", "993")),
    "user": os.getenv("IMAP_USER", "") or os.getenv("SMTP_USER", ""),
    "password": os.getenv("IMAP_PASSWORD", "") or os.getenv("SMTP_PASSWORD", ""),
}

imap_worker_state = {
    "running": False,
    "last_checked": None,
    "replies_found": 0,
    "total_checked": 0,
    "error": None,
}

_imap_lock = threading.Lock()


def _decode_header_value(value):
    """Decode MIME encoded header."""
    if not value:
        return ""
    decoded = decode_header(value)
    parts = []
    for part, charset in decoded:
        if isinstance(part, bytes):
            parts.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(part)
    return " ".join(parts)


def _imap_check_replies():
    """Connect to IMAP, search for replies to sent outreach emails."""
    conn = init_db()
    run_id = conn.execute(
        "INSERT INTO worker_runs (worker_type) VALUES (?)",
        ("imap_check",)
    ).lastrowid
    conn.commit()

    # Get all sent emails that haven't had replies detected
    sent = conn.execute(
        "SELECT eo.id, eo.recipient_email, eo.subject, eo.sent_at "
        "FROM email_outreach eo "
        "WHERE eo.status = 'sent' AND eo.reply_detected_at IS NULL "
        "ORDER BY eo.sent_at DESC LIMIT 200"
    ).fetchall()

    if not sent:
        return 0

    # Build lookup: email -> list of outreach records
    email_lookup = {}
    for row in sent:
        addr = (row["recipient_email"] or "").lower().strip()
        if addr:
            email_lookup.setdefault(addr, []).append(row)

    if not email_lookup:
        return 0

    imap_user = IMAP_CONFIG["user"]
    imap_pass = IMAP_CONFIG["password"]

    if not imap_user or not imap_pass:
        raise ValueError("IMAP credentials not configured (SMTP_USER/SMTP_PASSWORD)")

    # Connect to IMAP
    mail = imaplib.IMAP4_SSL(IMAP_CONFIG["host"], IMAP_CONFIG["port"])
    mail.login(imap_user, imap_pass)
    mail.select("INBOX", readonly=True)

    replies_found = 0
    total_checked = 0

    try:
        # Search for emails FROM any of our outreach recipients
        for recipient_email, outreach_rows in email_lookup.items():
            try:
                # Search for emails from this sender
                status, data = mail.search(None, f'(FROM "{recipient_email}")')
                if status != "OK" or not data[0]:
                    continue

                msg_ids = data[0].split()
                # Check most recent messages first
                for msg_id in reversed(msg_ids[-10:]):  # last 10 from this sender
                    total_checked += 1
                    try:
                        status, msg_data = mail.fetch(msg_id, "(RFC822)")
                        if status != "OK" or not msg_data or not msg_data[0]:
                            continue

                        raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
                        if not isinstance(raw, bytes):
                            continue
                        msg = email_lib.message_from_bytes(raw)

                        from_addr = _decode_header_value(msg.get("From", "")).lower()
                        subject = _decode_header_value(msg.get("Subject", ""))
                        date_str = msg.get("Date", "")

                        # Extract body preview
                        body_preview = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        body_preview = payload.decode("utf-8", errors="replace")[:300]
                                    break
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                body_preview = payload.decode("utf-8", errors="replace")[:300]

                        # Match to outreach records
                        for outreach in outreach_rows:
                            outreach_subject = outreach["subject"] or ""
                            # Match by: reply subject contains original subject, or from matches
                            is_reply = (
                                outreach_subject.lower() in subject.lower()
                                or f"re: {outreach_subject.lower()}" in subject.lower()
                                or subject.lower() in f"re: {outreach_subject.lower()}"
                            )

                            if is_reply or recipient_email in from_addr:
                                # Check if this reply is after the sent date
                                try:
                                    from email.utils import parsedate_to_datetime
                                    reply_dt = parsedate_to_datetime(date_str)
                                    sent_at = outreach["sent_at"]
                                    if sent_at and reply_dt.isoformat() < sent_at:
                                        continue  # Reply is before we sent — not a response
                                except Exception:
                                    pass

                                # Classify reply type
                                reply_type = _classify_reply(body_preview, subject)

                                # Record the reply
                                conn.execute(
                                    "UPDATE email_outreach SET reply_detected_at = datetime('now'), "
                                    "reply_preview = ?, status = 'replied', reply_type = ? WHERE id = ? AND reply_detected_at IS NULL",
                                    (body_preview[:300], reply_type, outreach["id"])
                                )

                                # Update pipeline stage
                                lead = conn.execute(
                                    "SELECT id, stage FROM pipeline_leads WHERE outreach_id = ?",
                                    (outreach["id"],)
                                ).fetchone()

                                if lead and lead["stage"] == "applied" and reply_type != "auto_reply":
                                    conn.execute(
                                        "UPDATE pipeline_leads SET stage = 'replied', updated_at = datetime('now') WHERE id = ?",
                                        (lead["id"],)
                                    )
                                    conn.execute(
                                        "INSERT INTO pipeline_events (lead_id, event_type, title, content) "
                                        "VALUES (?, 'email_reply', ?, ?)",
                                        (lead["id"],
                                         f"Reply Detected ({reply_type})",
                                         f"[{reply_type.upper()}] {body_preview[:150]}")
                                    )

                                conn.commit()
                                replies_found += 1
                                break  # Found reply for this outreach, move on

                    except Exception:
                        continue

            except Exception:
                continue

        # ── Bounce Detection ──
        # Search for mailer-daemon / delivery failure notifications
        for search_query in ['FROM "mailer-daemon"', 'SUBJECT "Address not found"', 'SUBJECT "Delivery Status Notification"', 'SUBJECT "Undeliverable"']:
            try:
                status, data = mail.search(None, f'({search_query})')
                if status != "OK" or not data[0]:
                    continue
                for msg_id in data[0].split()[-50:]:  # last 50
                    try:
                        status, msg_data = mail.fetch(msg_id, "(RFC822)")
                        if status != "OK" or not msg_data or not msg_data[0]:
                            continue
                        raw = msg_data[0][1]
                        if not isinstance(raw, bytes):
                            continue
                        msg = email_lib.message_from_bytes(raw)

                        # Extract body to find failed address
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        body = payload.decode("utf-8", errors="replace")
                                    break
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                body = payload.decode("utf-8", errors="replace")

                        # Find email addresses in the bounce body
                        bounced_emails = re.findall(r'[\w.+-]+@[\w.-]+\.\w{2,}', body)
                        bounced_emails = [e.lower() for e in bounced_emails
                                         if not any(x in e.lower() for x in ['google', 'postmaster', 'mailer-daemon', 'gmail-smtp', 'noreply'])]

                        for bounced_addr in bounced_emails:
                            # Check if this bounced address matches any of our sent emails
                            outreach = conn.execute(
                                "SELECT id FROM email_outreach WHERE recipient_email LIKE ? AND status = 'sent' AND error_type IS NULL LIMIT 1",
                                (f"%{bounced_addr}%",)
                            ).fetchone()
                            if outreach:
                                conn.execute(
                                    "UPDATE email_outreach SET status='failed', error_type='bounced', "
                                    "error_message=? WHERE id=?",
                                    (f"Address not found: {bounced_addr}", outreach["id"])
                                )
                                conn.commit()
                                replies_found += 1  # count bounces in the detection total
                    except Exception:
                        continue
            except Exception:
                continue

    finally:
        try:
            mail.close()
            mail.logout()
        except Exception:
            pass

    with _imap_lock:
        imap_worker_state["last_checked"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        imap_worker_state["replies_found"] = replies_found
        imap_worker_state["total_checked"] = total_checked

    conn.execute(
        "UPDATE worker_runs SET finished_at=datetime('now'), status=?, succeeded=?, failed=0, total=?, results=? WHERE id=?",
        ("completed", replies_found, total_checked, json.dumps({"replies_found": replies_found, "total_checked": total_checked}), run_id)
    )
    conn.commit()

    return replies_found


def _imap_poll_worker(interval_minutes=5):
    """Background thread: poll IMAP for replies every N minutes."""
    with _imap_lock:
        if imap_worker_state["running"]:
            return
        imap_worker_state["running"] = True
        imap_worker_state["error"] = None

    try:
        while imap_worker_state["running"]:
            try:
                found = _imap_check_replies()
                with _imap_lock:
                    imap_worker_state["error"] = None
            except Exception as e:
                with _imap_lock:
                    imap_worker_state["error"] = str(e)

            # Sleep in small increments so we can stop quickly
            for _ in range(interval_minutes * 60):
                if not imap_worker_state["running"]:
                    break
                time.sleep(1)
    finally:
        with _imap_lock:
            imap_worker_state["running"] = False


def start_imap_polling(interval_minutes=5):
    """Start IMAP polling in a background thread."""
    if imap_worker_state["running"]:
        return {"status": "already_running", **imap_worker_state}
    t = threading.Thread(target=_imap_poll_worker, args=(interval_minutes,), daemon=True)
    t.start()
    return {"status": "started", "interval_minutes": interval_minutes}


def stop_imap_polling():
    """Stop the IMAP polling worker."""
    imap_worker_state["running"] = False
    return {"status": "stopped"}


def check_replies_once():
    """Run a single IMAP check (not polling, just one scan)."""
    try:
        found = _imap_check_replies()
        return {"status": "ok", "replies_found": found, "last_checked": imap_worker_state.get("last_checked")}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_imap_status():
    """Get current IMAP worker status."""
    return dict(imap_worker_state)
