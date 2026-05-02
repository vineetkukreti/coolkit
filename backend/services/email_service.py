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
    "from_name": os.getenv("FROM_NAME", ""),
}

# ───────────────────────────────────────────────
# Email blocklist (never send outreach to these)
# ───────────────────────────────────────────────

# Domains that must never receive outreach (exact domain match only)
_employer_domain = PROFILE.get("employer_domain", "")
BLOCKED_DOMAINS = {
    *([_employer_domain] if _employer_domain else []),  # current employer (from profile)
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
    "vodafoneidea.com",   # bounces
    "anantamhr.com",      # bounces
    "cgi.com",            # bounces (malformed addresses)
    "costaffglobal.com",  # bounces
    "nlb.tech.com",       # bounces (fake recruiter domain)
    "themuse.com",        # bounces (job board, not real company)
    "accentureglobalco.com",  # bounces (fake/typo Accenture domain)
}

# Company keywords — matched against company name only (word boundary, not substring)
_employer_name = PROFILE.get("employer", "").lower()
BLOCKED_COMPANIES = [
    *([_employer_name] if _employer_name else []),  # current employer (from profile)
]

# Keep legacy name for any external imports
EMAIL_BLOCKLIST = list(BLOCKED_DOMAINS) + BLOCKED_COMPANIES


def _is_blocked_email(email: str, company: str = "") -> bool:
    """Check if email domain is blocked or company is current employer.

    - Domains: exact match on email domain (no substring risk)
    - Companies: word-boundary match on company name only
    """
    email = email.lower().strip()

    # Extract domain from email (handle comma-separated)
    if "," in email:
        email = email.split(",")[0].strip()
    if "@" in email:
        domain = email.rsplit("@", 1)[1]
        if domain in BLOCKED_DOMAINS:
            return True

    # Company check: only match if the keyword appears as a standalone word
    if company:
        company_lower = company.lower()
        for kw in BLOCKED_COMPANIES:
            if kw in company_lower.split() or kw in company_lower.replace("-", " ").replace("_", " ").split():
                return True

    return False


# ───────────────────────────────────────────────
# Bounce history — learn from past failures
# ───────────────────────────────────────────────

# Domain bounce threshold: if a domain has this many bounces, auto-block it
BOUNCE_DOMAIN_THRESHOLD = 2

# Major email providers — never block the whole domain, only individual addresses
MAJOR_PROVIDERS = {
    "gmail.com", "yahoo.com", "yahoo.in", "outlook.com", "hotmail.com",
    "live.com", "aol.com", "icloud.com", "protonmail.com", "zoho.com",
    "rediffmail.com", "yandex.com", "mail.com",
}

# Cache for bounced domains (refreshed per bulk run)
_bounced_domains_cache = {"domains": set(), "emails": set(), "loaded_at": 0}
_bounce_cache_lock = threading.Lock()


def _refresh_bounce_cache(conn=None):
    """Load bounced emails and domains from DB into memory cache.
    Refreshes at most once per 60 seconds.
    """
    with _bounce_cache_lock:
        if time.time() - _bounced_domains_cache["loaded_at"] < 60:
            return  # fresh enough

    close_conn = False
    if conn is None:
        conn = init_db()
        close_conn = True

    try:
        # Get all bounced email addresses
        bounced_rows = conn.execute(
            "SELECT DISTINCT recipient_email FROM email_outreach "
            "WHERE error_type = 'bounced' OR (status = 'failed' AND error_type = 'invalid_address')"
        ).fetchall()
        bounced_emails = set()
        for r in bounced_rows:
            email = r["recipient_email"].lower().strip()
            if "," in email:
                email = email.split(",")[0].strip()
            bounced_emails.add(email)

        # Count bounces per domain, auto-block domains with 2+ bounces
        domain_counts = conn.execute(
            """SELECT SUBSTR(
                CASE WHEN recipient_email LIKE '%,%'
                     THEN TRIM(SUBSTR(recipient_email, 1, INSTR(recipient_email, ',') - 1))
                     ELSE TRIM(recipient_email)
                END,
                INSTR(
                    CASE WHEN recipient_email LIKE '%,%'
                         THEN TRIM(SUBSTR(recipient_email, 1, INSTR(recipient_email, ',') - 1))
                         ELSE TRIM(recipient_email)
                    END, '@') + 1
               ) as domain,
               COUNT(*) as cnt
               FROM email_outreach
               WHERE error_type = 'bounced' OR (status = 'failed' AND error_type = 'invalid_address')
               GROUP BY domain
               HAVING cnt >= ?""",
            (BOUNCE_DOMAIN_THRESHOLD,)
        ).fetchall()
        bounced_domains = {r["domain"].lower() for r in domain_counts if r["domain"] and r["domain"].lower() not in MAJOR_PROVIDERS}

        with _bounce_cache_lock:
            _bounced_domains_cache["emails"] = bounced_emails
            _bounced_domains_cache["domains"] = bounced_domains
            _bounced_domains_cache["loaded_at"] = time.time()

    finally:
        if close_conn:
            conn.close()


def _is_bounce_blocked(email: str, conn=None) -> tuple:
    """Check if email or its domain has bounced before.
    Returns (blocked: bool, reason: str).
    """
    _refresh_bounce_cache(conn)
    email_lower = email.lower().strip()

    with _bounce_cache_lock:
        # Exact email match
        if email_lower in _bounced_domains_cache["emails"]:
            return True, f"Previously bounced: {email_lower}"

        # Domain match (2+ bounces from same domain)
        if "@" in email_lower:
            domain = email_lower.rsplit("@", 1)[1]
            if domain in _bounced_domains_cache["domains"]:
                return True, f"Domain '{domain}' has {BOUNCE_DOMAIN_THRESHOLD}+ previous bounces — auto-blocked"

    return False, ""


def get_bounce_blocked_domains(conn=None) -> list:
    """Return list of domains auto-blocked due to bounce history. Used by stats endpoint."""
    _refresh_bounce_cache(conn)
    with _bounce_cache_lock:
        return sorted(_bounced_domains_cache["domains"])


# ───────────────────────────────────────────────
# Suspicious email pattern detection
# ───────────────────────────────────────────────

def _looks_suspicious(email: str, company: str = "") -> tuple:
    """Detect email patterns that almost always bounce.
    Returns (suspicious: bool, reason: str).
    """
    if "@" not in email:
        return True, "No @ sign"

    local, domain = email.rsplit("@", 1)

    # Gibberish local part: too short or random consonant clusters
    if len(local) <= 2 and not local.isalpha():
        return True, f"Suspiciously short local part: '{local}'"

    # Company name used as email local part (e.g., flatiron.health@flatiron.com)
    if company:
        company_clean = re.sub(r'[^a-z0-9]', '', company.lower())
        local_clean = re.sub(r'[^a-z0-9]', '', local.lower())
        if company_clean and len(company_clean) > 3 and local_clean == company_clean:
            return True, f"Local part is just the company name: {email}"

    # Domain part of company name stuffed into local part
    domain_name = domain.split(".")[0].lower()
    if domain_name and len(domain_name) > 3:
        local_lower = local.lower().replace(".", "")
        if local_lower == domain_name or local_lower == f"{domain_name}health" or local_lower == f"{domain_name}ai":
            return True, f"Local part mirrors domain name: {email}"

    # Fake/placeholder patterns
    if re.match(r'^[a-z]xxx', local.lower()) or re.match(r'^xxx', local.lower()):
        return True, f"Placeholder email pattern: {email}"

    # Suspiciously generic startup domains
    FAKE_DOMAINS = {"stealthstartup.io", "example.com", "test.com", "startup.com"}
    if domain.lower() in FAKE_DOMAINS:
        return True, f"Fake/placeholder domain: {domain}"

    return False, ""


# ───────────────────────────────────────────────
# Public wrappers for route access
# ───────────────────────────────────────────────

def generate_email(post_data: dict) -> dict:
    """Public wrapper: generate personalized cold email using AI."""
    return _generate_email_with_gemini(post_data)


def send_email(to_email: str, subject: str, body: str, attach_resume: bool = False) -> dict:
    """Public wrapper: send email via SMTP."""
    return _send_email_smtp(to_email, subject, body, attach_resume=attach_resume)


def is_email_blocked(email: str, company: str = "") -> bool:
    """Public wrapper: check if email/company is on the blocklist."""
    return _is_blocked_email(email, company)


def verify_email(email: str, company: str = "", skip_smtp: bool = False) -> dict:
    """Public wrapper: full pre-send verification."""
    return verify_before_send(email, company, skip_smtp=skip_smtp)


# ───────────────────────────────────────────────
# Email generation agent (Gemini 2.5 Flash Lite)
# ───────────────────────────────────────────────

def _build_email_agent_prompt():
    """Build the email agent prompt dynamically from PROFILE."""
    first_name = PROFILE.get("first_name", "") or PROFILE.get("name", "").split()[0] if PROFILE.get("name") else "User"
    name = PROFILE.get("name", first_name)
    title = PROFILE.get("current_title", "Engineer")
    exp_years = PROFILE.get("experience_years", 0)
    location = PROFILE.get("location", "")
    employer = PROFILE.get("employer", "")
    linkedin = PROFILE.get("linkedin", "")
    github = PROFILE.get("github", "")
    skills_summary = PROFILE.get("skills_summary", ", ".join(list(RESUME_SKILLS.keys())[:15]))
    education = PROFILE.get("education", "")

    # Build profile section
    profile_lines = [f"Name: {name}"]
    title_line = f"Title: {title}"
    if exp_years:
        title_line += f" | {exp_years} years experience"
    profile_lines.append(title_line)
    if location:
        profile_lines.append(f"Location: {location}")
    if linkedin:
        profile_lines.append(f"LinkedIn: {linkedin}")
    if github:
        profile_lines.append(f"GitHub: {github}")

    # Current role
    role_lines = []
    if employer:
        role_lines.append(f"- {title} at {employer}")
    if skills_summary:
        role_lines.append(f"\nStrong experience in:\n{skills_summary}")

    # Projects
    projects = PROFILE.get("projects", [])
    project_section = ""
    if projects:
        project_section = "\nProjects (pick 2-3 that BEST match the target role):\n"
        for i, proj in enumerate(projects, 1):
            pname = proj.get("name", f"Project {i}")
            pdesc = proj.get("description", "")
            project_section += f"{i}. {pname}"
            if pdesc:
                project_section += f" — {pdesc}"
            project_section += "\n"

    # Achievements
    achievements = PROFILE.get("achievements", [])
    achievement_section = ""
    if achievements:
        achievement_section = "\nACHIEVEMENTS:\n"
        for ach in achievements:
            if ach:
                achievement_section += f"- {ach}\n"
    if education:
        achievement_section += f"- {education}\n"

    profile_block = "\n".join(profile_lines)
    if role_lines:
        profile_block += "\n\nCURRENT ROLE:\n" + "\n".join(role_lines)
    profile_block += project_section + achievement_section

    return f"""You are an AI job outreach assistant specialized in generating highly personalized, human-like recruiter emails.

Your goal is to maximize recruiter response rate.

You will receive structured data about a hiring post. Some fields may be missing or incomplete. You must intelligently adapt.

━━━ CANDIDATE PROFILE (IMPORTANT CONTEXT) ━━━

{profile_block}

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
12. Sign off with just "Best,\\n{first_name}" — not "Best regards, {name}"

━━━ EMAIL STRUCTURE ━━━

1. Opening hook + identity — reference something SPECIFIC from their post AND naturally identify yourself in the same 1-2 sentences. Do NOT use a formal intro like "My name is ... and I am..." — weave who you are into the hook naturally.
2. Context match — 2-3 lines showing what YOU built that solves THEIR specific problem. Use concrete numbers/details. Connect YOUR work to THEIR needs with a clear "you need X → I built X" mapping.
3. Specific value — pick 1 specific problem from their post and show you've solved it before. Emphasize end-to-end system thinking, not just modeling.
4. Close — polite + confident, one clear low-friction ask. Mention resume attached.
5. Sign off — "Best,\\n{first_name}"

━━━ ADAPTATION RULES ━━━

IF is_hiring=true AND role+company known:
  → Direct application. Reference the specific role. Match relevant projects to their requirements.

IF is_hiring=true BUT role/company vague:
  → Infer the role from post content. Be specific about what you'd bring.

IF is_hiring=false OR weak signal:
  → Value-first outreach. Lead with curiosity about their work/domain. Position as "interested in what you're building" not "give me a job".

━━━ OUTPUT FORMAT (EXACT) ━━━

Return ONLY this, nothing else:

Subject: <clear, role-focused subject line>

<email body starting directly with "Hi {{author_first_name}}," then the hook — no "Email:" label>

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
- Weak content → focus on domain relevance"""


EMAIL_AGENT_PROMPT = _build_email_agent_prompt()


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
    data = resp.json()
    candidates = data.get("candidates")
    if not candidates or not isinstance(candidates, list) or len(candidates) == 0:
        return {"subject": "", "body": "", "error": "Gemini returned no candidates"}
    content = candidates[0].get("content")
    if not content or not content.get("parts") or len(content["parts"]) == 0:
        return {"subject": "", "body": "", "error": "Gemini response missing content parts"}
    text = content["parts"][0].get("text", "")
    if not text:
        return {"subject": "", "body": "", "error": "Gemini returned empty text"}

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
        "[Your Name]": PROFILE.get("first_name", "") or PROFILE.get("name", "").split()[0] if PROFILE.get("name") else "",
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
    full_name = PROFILE.get("name", "")
    first_name_p = PROFILE.get("first_name", "") or (full_name.split()[0] if full_name else "")
    if full_name and body.endswith(full_name):
        body = body[:-len(full_name)].rstrip().rstrip(",").rstrip()
        body += f"\n{first_name_p}"

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


# ───────────────────────────────────────────────
# Robust pre-send email verification
# ───────────────────────────────────────────────

# Generic prefixes that almost always bounce (not real mailboxes)
GENERIC_PREFIXES = (
    'info@', 'careers@', 'hr@', 'support@', 'contact@', 'hello@',
    'jobs@', 'hiring@', 'team@', 'recruitment@', 'apply@',
    'noreply@', 'no-reply@', 'admin@', 'office@', 'general@',
)


def sanitize_email(email: str) -> str:
    """Clean and fix common email malformations.

    Fixes: leading dots, concatenated domains, whitespace, comma-separated,
    trailing punctuation, double @, control chars.
    Returns cleaned email or empty string if unfixable.
    """
    if not email:
        return ""

    email = email.strip()

    # Handle comma-separated — take the first one
    if "," in email:
        email = email.split(",")[0].strip()

    # Remove control chars and whitespace
    email = re.sub(r'[\r\n\t]', '', email)
    email = email.strip().lower()

    if "@" not in email:
        return ""

    # Fix double @@ (typo)
    email = email.replace("@@", "@")

    local, domain = email.rsplit("@", 1)

    # Fix leading dots in local part (e.g., .ban.india@cgi.com)
    local = local.lstrip(".")
    # Fix trailing dots in local part
    local = local.rstrip(".")

    # Fix concatenated domains (e.g., gmail.comcoimbatore -> gmail.com)
    # Detect: valid TLD followed by 3+ extra non-dot chars (avoids false positives like .com -> .co)
    domain_fix = re.match(r'^([a-z0-9.-]+\.(com|org|net|io|ai|in|co|tech|health|edu|gov|us|uk|ca|au))[a-z]{3,}$', domain)
    if domain_fix:
        domain = domain_fix.group(1)

    # Strip trailing dots/punctuation from domain
    domain = domain.rstrip(".,;:!?")

    # Basic sanity
    if not local or not domain or "." not in domain:
        return ""
    if len(local) > 64 or len(domain) > 253:
        return ""

    return f"{local}@{domain}"


def _smtp_rcpt_check(email: str, timeout: int = 8) -> str:
    """SMTP RCPT TO verification — asks the mail server if address exists.

    Returns: "accepted", "rejected", or "unknown"
    Does NOT send any email.
    """
    domain = email.split("@")[1] if "@" in email else ""
    if not domain:
        return "rejected"

    try:
        mx_answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        mx_host = str(list(mx_answers)[0].exchange).rstrip(".")
    except Exception:
        return "rejected"  # No MX = no mail server

    try:
        smtp = smtplib.SMTP(timeout=timeout)
        smtp.connect(mx_host, 25)
        smtp.helo("verify.local")
        smtp.mail("verify@verify.local")
        code, _ = smtp.rcpt(email)
        smtp.quit()
        if code == 250:
            return "accepted"
        if code >= 550:
            return "rejected"
        return "unknown"
    except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError,
            socket.timeout, socket.gaierror, ConnectionRefusedError, OSError):
        return "unknown"
    except Exception:
        return "unknown"


def verify_before_send(email: str, company: str = "", skip_smtp: bool = False) -> dict:
    """Full pre-send verification gate. Run this before every send.

    Pipeline: sanitize → blocklist → bounce history → suspicious pattern →
              generic filter → format → MX → SMTP RCPT TO

    Args:
        email: raw email address (may be malformed or comma-separated)
        company: company name for blocklist check
        skip_smtp: if True, skip SMTP RCPT TO (for speed in bulk-generate)

    Returns: {valid, email, reason, smtp_status}
        - valid: True/False
        - email: sanitized email (use this for sending)
        - reason: human-readable explanation
        - smtp_status: "accepted"/"rejected"/"unknown"/"skipped"
    """
    result = {"valid": False, "email": "", "reason": "", "smtp_status": "skipped"}

    # Step 1: Sanitize
    clean = sanitize_email(email)
    if not clean:
        result["reason"] = f"Unfixable malformed email: {email}"
        return result
    result["email"] = clean

    # Step 2: Blocklist
    if _is_blocked_email(clean, company):
        result["reason"] = f"Blocked domain: {clean}"
        return result

    # Step 3: Bounce history check — never send to emails/domains that already bounced
    bounce_blocked, bounce_reason = _is_bounce_blocked(clean)
    if bounce_blocked:
        result["reason"] = bounce_reason
        return result

    # Step 4: Suspicious pattern detection — catch obviously fake emails
    suspicious, suspicious_reason = _looks_suspicious(clean, company)
    if suspicious:
        result["reason"] = f"Suspicious email pattern: {suspicious_reason}"
        return result

    # Step 5: Generic address filter
    if clean.startswith(GENERIC_PREFIXES):
        result["reason"] = f"Generic address (high bounce risk): {clean}"
        return result

    # Step 6: Format check
    if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', clean):
        result["reason"] = f"Invalid email format: {clean}"
        return result

    # Step 7: MX check
    domain = clean.split("@")[1]
    try:
        dns.resolver.resolve(domain, "MX", lifetime=5)
    except Exception:
        result["reason"] = f"Domain '{domain}' has no mail server (no MX records)"
        return result

    # Step 8: SMTP RCPT TO verification
    if skip_smtp:
        result["valid"] = True
        result["reason"] = "Passed (SMTP skipped)"
        result["smtp_status"] = "skipped"
        return result

    smtp_status = _smtp_rcpt_check(clean)
    result["smtp_status"] = smtp_status

    if smtp_status == "rejected":
        result["reason"] = f"Mail server rejected address: {clean}"
        return result

    # accepted or unknown = pass (fail-open for unknown, some servers don't support RCPT TO check)
    result["valid"] = True
    result["reason"] = f"Verified ({smtp_status})"
    return result


def verify_best_email(email_field: str, company: str = "", skip_smtp: bool = False) -> dict:
    """Try each email in a comma-separated list, return the first valid one.

    Falls back through alternatives when the first email fails validation
    (e.g., 'info@co.com, jane@co.com' → skips generic info@, uses jane@).
    """
    if "," not in email_field:
        return verify_before_send(email_field, company, skip_smtp)

    candidates = [e.strip() for e in email_field.split(",") if e.strip()]
    last_result = None
    for candidate in candidates:
        result = verify_before_send(candidate, company, skip_smtp)
        if result["valid"]:
            return result
        last_result = result

    # All failed — return the last failure reason
    return last_result or {"valid": False, "email": "", "reason": "No valid email in list", "smtp_status": "skipped"}


def _send_email_smtp(to_email: str, subject: str, body: str, attach_resume: bool = False, resume_path: str = "") -> dict:
    """Send email via SMTP (Gmail). Optionally attach resume PDF."""
    # Handle comma-separated addresses — send to first valid one
    if "," in to_email:
        addresses = [a.strip() for a in to_email.split(",") if a.strip()]
        to_email = addresses[0]  # Use first address as primary recipient

    cfg = SMTP_CONFIG
    if not cfg["password"]:
        raise ValueError("SMTP_PASSWORD not set in .env. Generate a Gmail App Password first.")

    # Sanitize headers to prevent header injection
    to_email = to_email.replace("\r", "").replace("\n", "")
    subject = subject.replace("\r", "").replace("\n", "")

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
        resume_path = Path(resume_path) if resume_path else Path(PROFILE.get("resume_path", ""))
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
    check = verify_before_send(to_email)
    if not check["valid"]:
        return {"success": False, "error": check["reason"]}
    clean_email = check["email"]
    try:
        result = _send_email_smtp(clean_email, subject, body, attach_resume=True, resume_path=resume_path)
        if result["status"] == "sent":
            return {"success": True}
        return {"success": False, "error": result.get("error_message", "Send failed")[:300]}
    except Exception as e:
        return {"success": False, "error": str(e)[:300]}


# ───────────────────────────────────────────────
# Background email workers (non-blocking)
# ───────────────────────────────────────────────

_email_lock = threading.Lock()  # kept for backward compat

# Separate worker states so generate + send can run in parallel
_generate_lock = threading.Lock()
_send_lock = threading.Lock()

generate_worker_state = {
    "running": False,
    "task": "generating",
    "current": 0,
    "total": 0,
    "current_label": "",
    "succeeded": 0,
    "failed": 0,
    "skipped": 0,
    "results": [],
    "error": None,
}

send_worker_state = {
    "running": False,
    "task": "sending",
    "current": 0,
    "total": 0,
    "current_label": "",
    "succeeded": 0,
    "failed": 0,
    "skipped": 0,
    "results": [],
    "error": None,
}

# Legacy alias — routes that import email_worker_state still work (points to generate by default)
email_worker_state = generate_worker_state


def _bulk_generate_worker(post_ids: list[int]):
    """Background thread: generate emails for given post/lead IDs.

    Positive IDs = posts table, negative IDs = startup_leads table.
    """
    conn = None
    run_id = None
    succeeded_count = 0
    failed_count = 0
    try:
        conn = init_db()
        run_id = conn.execute(
            "INSERT INTO worker_runs (worker_type, total) VALUES (?, ?)",
            ("bulk_generate", len(post_ids))
        ).lastrowid
        conn.commit()

        with _generate_lock:
            generate_worker_state["running"] = True
            generate_worker_state["total"] = len(post_ids)
            generate_worker_state["current"] = 0
            generate_worker_state["succeeded"] = 0
            generate_worker_state["failed"] = 0
            generate_worker_state["skipped"] = 0
            generate_worker_state["results"] = []
            generate_worker_state["error"] = None

        for i, post_id in enumerate(post_ids):
            with _generate_lock:
                if not generate_worker_state["running"]:
                    break
                generate_worker_state["current"] = i + 1

            # Negative IDs = startup leads, positive = posts
            if post_id < 0:
                lead_id = -post_id
                lead = conn.execute(
                    """SELECT id, company_name, email, description, industry, location,
                              website, linkedin_url, tags
                       FROM startup_leads WHERE id = ?""",
                    (lead_id,),
                ).fetchone()
                if not lead:
                    with _generate_lock:
                        generate_worker_state["failed"] += 1
                        generate_worker_state["results"] = generate_worker_state["results"][-19:] + [{"post_id": post_id, "status": "error", "message": "Lead not found"}]
                    failed_count += 1
                    continue
                lead = dict(lead)
                row = {
                    "id": lead["id"],
                    "author_name": lead["company_name"],
                    "author_headline": lead.get("industry") or "Healthcare Startup",
                    "author_profile": lead.get("linkedin_url") or "",
                    "email": lead["email"],
                    "content": lead.get("description") or "",
                    "links": lead.get("website") or "",
                    "domain_relevance": "High",
                    "is_hiring": 0,
                    "role": lead.get("tags") or "",
                    "company": lead["company_name"],
                    "location": lead.get("location") or "",
                    "post_url": lead.get("website") or "",
                    "source_type": "startup_lead",
                }
            else:
                row = conn.execute(
                    """SELECT p.id, p.author_name, p.author_headline, p.content, p.email,
                              p.links, p.domain_relevance, p.is_hiring, p.post_url,
                              j.role, j.company, j.location, j.experience
                       FROM posts p LEFT JOIN jobs j ON j.post_id = p.id
                       WHERE p.id = ?""",
                    (post_id,),
                ).fetchone()
                if not row:
                    with _generate_lock:
                        generate_worker_state["failed"] += 1
                        generate_worker_state["results"] = generate_worker_state["results"][-19:] + [{"post_id": post_id, "status": "error", "message": "Post not found"}]
                    failed_count += 1
                    continue
                row = dict(row)

            # Full pre-generate verification — tries all comma-separated alternatives
            check = verify_best_email(row.get("email", ""), row.get("company", ""), skip_smtp=True)
            if not check["valid"]:
                with _generate_lock:
                    generate_worker_state["skipped"] += 1
                    generate_worker_state["results"] = generate_worker_state["results"][-19:] + [{"post_id": post_id, "status": "skipped", "message": check["reason"]}]
                failed_count += 1
                continue

            to_email = check["email"]  # Use sanitized email

            with _generate_lock:
                generate_worker_state["current_label"] = f"{row.get('author_name', '?')} | {row.get('role', '?')} @ {row.get('company', '?')}"

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
                except Exception as e:
                    print(f"[BulkGenerate] Referral lookup failed for {company}: {e}")

            # Dedup: skip if we already emailed this recipient
            existing = conn.execute(
                "SELECT id FROM email_outreach WHERE recipient_email = ? AND status IN ('sent', 'replied', 'draft')",
                (to_email,)
            ).fetchone()
            if existing:
                with _generate_lock:
                    generate_worker_state["skipped"] += 1
                    generate_worker_state["results"] = generate_worker_state["results"][-19:] + [{"post_id": post_id, "status": "skipped", "message": f"Already emailed {to_email}"}]
                failed_count += 1
                continue

            try:
                email = _generate_email_with_gemini(row)
                # Save draft to DB — use real post_id for posts, NULL for startup leads
                db_post_id = post_id if post_id > 0 else None
                existing = conn.execute(
                    "SELECT id FROM email_outreach WHERE recipient_email = ? AND status = 'draft'", (to_email,),
                ).fetchone()
                cursor = conn.cursor()
                if existing:
                    cursor.execute(
                        "UPDATE email_outreach SET post_id=?, recipient_email=?, subject=?, body=?, created_at=datetime('now') WHERE id=?",
                        (db_post_id, to_email, email["subject"], email["body"], existing["id"]),
                    )
                    outreach_id = existing["id"]
                else:
                    cursor.execute(
                        "INSERT INTO email_outreach (post_id, recipient_email, subject, body, status) VALUES (?, ?, ?, ?, 'draft')",
                        (db_post_id, to_email, email["subject"], email["body"]),
                    )
                    outreach_id = cursor.lastrowid
                conn.commit()
                try:
                    record_variant(conn, outreach_id, variant, variant_strategies.get(variant, ""))
                    cursor.execute("UPDATE email_outreach SET outreach_type = ? WHERE id = ?", (outreach_type, outreach_id))
                    conn.commit()
                except Exception as e:
                    print(f"[BulkGenerate] Variant recording failed for outreach {outreach_id}: {e}")
                with _generate_lock:
                    generate_worker_state["succeeded"] += 1
                    generate_worker_state["results"] = generate_worker_state["results"][-19:] + [{
                        "post_id": post_id, "status": "ok",
                        "to_email": to_email, "author_name": row.get("author_name", ""),
                        **email,
                    }]
                succeeded_count += 1
            except Exception as e:
                with _generate_lock:
                    generate_worker_state["failed"] += 1
                    generate_worker_state["results"] = generate_worker_state["results"][-19:] + [{"post_id": post_id, "status": "error", "message": str(e)[:200]}]
                failed_count += 1

            # Rate limit delay between API calls
            time.sleep(random.uniform(1, 2))

        if conn and run_id:
            conn.execute(
                "UPDATE worker_runs SET finished_at=datetime('now'), status=?, succeeded=?, failed=?, results=? WHERE id=?",
                ("completed", succeeded_count, failed_count, json.dumps(generate_worker_state.get("results", [])[-20:]), run_id)
            )
            conn.commit()
    except Exception as e:
        print(f"[BulkGenerate] Worker crashed: {e}")
        with _generate_lock:
            generate_worker_state["error"] = str(e)[:500]
        if conn and run_id:
            try:
                conn.execute(
                    "UPDATE worker_runs SET finished_at=datetime('now'), status=?, results=? WHERE id=?",
                    ("failed", json.dumps({"error": str(e)[:300]}), run_id)
                )
                conn.commit()
            except Exception:
                pass
    finally:
        with _generate_lock:
            generate_worker_state["running"] = False
            generate_worker_state["current_label"] = ""
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _bulk_send_worker(attach_resume: bool = True):
    """Background thread: send all draft emails."""
    conn = None
    run_id = None
    succeeded_count = 0
    failed_count = 0
    try:
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

        with _send_lock:
            send_worker_state["running"] = True
            send_worker_state["total"] = len(drafts)
            send_worker_state["current"] = 0
            send_worker_state["succeeded"] = 0
            send_worker_state["failed"] = 0
            send_worker_state["skipped"] = 0
            send_worker_state["results"] = []
            send_worker_state["error"] = None

        for i, draft in enumerate(drafts):
            with _send_lock:
                if not send_worker_state["running"]:
                    break
                send_worker_state["current"] = i + 1

            # Full pre-send verification — tries all comma-separated alternatives
            check = verify_best_email(draft["recipient_email"])
            if not check["valid"]:
                with _send_lock:
                    send_worker_state["skipped"] += 1
                    send_worker_state["results"] = send_worker_state["results"][-19:] + [{"post_id": draft["post_id"], "to": draft["recipient_email"], "status": "skipped", "message": check["reason"]}]
                # Mark as failed in DB so we don't retry
                conn.execute(
                    "UPDATE email_outreach SET status='failed', error_message=?, error_type='pre_send_rejected' WHERE id=?",
                    (check["reason"][:500], draft["id"])
                )
                conn.commit()
                failed_count += 1
                continue

            # Use sanitized email
            clean_email = check["email"]

            # Dedup: skip if recipient already has a 'sent' record (different outreach entry)
            already_sent = conn.execute(
                "SELECT id FROM email_outreach WHERE recipient_email = ? AND status = 'sent' AND id != ?",
                (clean_email, draft["id"])
            ).fetchone()
            if already_sent:
                with _send_lock:
                    send_worker_state["skipped"] += 1
                    send_worker_state["results"] = send_worker_state["results"][-19:] + [{"post_id": draft["post_id"], "to": clean_email, "status": "skipped", "message": f"Already sent to {clean_email}"}]
                failed_count += 1
                continue

            with _send_lock:
                send_worker_state["current_label"] = f"{clean_email} ({check['smtp_status']})"

            result = _send_email_smtp(clean_email, draft["subject"], draft["body"], attach_resume=attach_resume)
            if result["status"] == "sent":
                conn.execute(
                    "UPDATE email_outreach SET status='sent', sent_at=datetime('now') WHERE id=?",
                    (draft["id"],),
                )
                conn.commit()
                with _send_lock:
                    send_worker_state["succeeded"] += 1
                    send_worker_state["results"] = send_worker_state["results"][-19:] + [{"post_id": draft["post_id"], "to": draft["recipient_email"], "status": "sent"}]
                succeeded_count += 1
            else:
                conn.execute(
                    "UPDATE email_outreach SET status='failed', error_message=?, error_type=? WHERE id=?",
                    (result.get("error_message", "")[:500], result.get("error_type", "unknown"), draft["id"])
                )
                conn.commit()
                with _send_lock:
                    send_worker_state["failed"] += 1
                    send_worker_state["results"] = send_worker_state["results"][-19:] + [{"post_id": draft["post_id"], "to": draft["recipient_email"], "status": "failed", "error": result.get("error_message", "")[:200]}]
                failed_count += 1

            # Anti-spam delay
            time.sleep(random.uniform(3, 8))

        if conn and run_id:
            conn.execute(
                "UPDATE worker_runs SET finished_at=datetime('now'), status=?, succeeded=?, failed=?, results=? WHERE id=?",
                ("completed", succeeded_count, failed_count, json.dumps(send_worker_state.get("results", [])[-20:]), run_id)
            )
            conn.commit()
    except Exception as e:
        print(f"[BulkSend] Worker crashed: {e}")
        with _send_lock:
            send_worker_state["error"] = str(e)[:500]
        if conn and run_id:
            try:
                conn.execute(
                    "UPDATE worker_runs SET finished_at=datetime('now'), status=?, results=? WHERE id=?",
                    ("failed", json.dumps({"error": str(e)[:300]}), run_id)
                )
                conn.commit()
            except Exception:
                pass
    finally:
        with _send_lock:
            send_worker_state["running"] = False
            send_worker_state["current_label"] = ""
        if conn:
            try:
                conn.close()
            except Exception:
                pass


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
        "SELECT eo.*, pl.company as pl_company, pl.role as pl_role, pl.recipient_name as pl_name, "
        "p.content, p.author_name, "
        "(SELECT j.role FROM jobs j WHERE j.post_id = eo.post_id LIMIT 1) as job_role, "
        "(SELECT j2.company FROM jobs j2 WHERE j2.post_id = eo.post_id LIMIT 1) as job_company "
        "FROM email_outreach eo "
        "LEFT JOIN pipeline_leads pl ON pl.outreach_id = eo.id "
        "LEFT JOIN posts p ON p.id = eo.post_id "
        "WHERE eo.id = ?", (outreach_id,)
    ).fetchone()
    if not row:
        return None

    row = dict(row)
    followup_num = (row.get("followup_count") or 0) + 1
    original_subject = row.get("subject") or "your previous email"
    recipient = row.get("recipient_email") or ""
    original_body = row.get("body") or ""

    # Resolve company and role from multiple sources
    company = (row.get("job_company") or row.get("pl_company") or "").strip()
    if not company:
        # Extract from email domain
        domain = recipient.split("@")[1].split(".")[0] if "@" in recipient else ""
        generic = {"gmail", "yahoo", "hotmail", "outlook", "protonmail"}
        company = domain.title() if domain and domain.lower() not in generic else ""

    role = (row.get("job_role") or row.get("pl_role") or "").strip()
    if not role:
        # Extract from email subject (before first separator)
        subj = original_subject
        for sep in [" | ", " — ", " - ", " – "]:
            if sep in subj:
                role = subj.split(sep)[0].strip()
                break
        if not role:
            role = subj[:50].strip()

    recipient_name = (row.get("pl_name") or row.get("author_name") or "").strip()
    greeting = f"Hi {recipient_name.split()[0]}," if recipient_name else "Hi,"

    first_name = PROFILE.get("first_name", "") or (PROFILE.get("name", "").split()[0] if PROFILE.get("name") else "")

    prompt = f"""You are writing follow-up email #{followup_num} for a job application cold outreach.

ORIGINAL EMAIL SUBJECT: {original_subject}
ORIGINAL EMAIL BODY (first 300 chars): {original_body[:300]}
RECIPIENT: {recipient}
RECIPIENT NAME: {recipient_name or "Unknown"}
COMPANY: {company or "Unknown"}
ROLE: {role}
YOUR NAME: {first_name}

RULES:
- Keep it SHORT: 50-80 words maximum
- Start with "{greeting}"
- Reference the original email briefly ("Following up on my email about...")
- Add ONE new piece of value (a recent project, a relevant insight, or a specific idea for them)
- Be respectful of their time
- End with a soft call to action ("Would love to chat" or "Happy to share more")
- No "just checking in" or "touching base" — add real value
- Sign off with just your first name
- Subject line: "Re: {original_subject}" (keep the thread)

OUTPUT FORMAT (exactly this):
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

    # Fallback template
    return {
        "subject": f"Re: {original_subject}",
        "body": f"{greeting}\n\nFollowing up on my previous email about the {role} opportunity{(' at ' + company) if company else ''}. I've been working on some relevant projects since and would love to share how my experience could add value to your team.\n\nHappy to jump on a quick call whenever works.\n\nBest,\n{first_name}"
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
    with _followup_lock:
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
    text = ((body or "") + " " + (subject or "")).lower()

    # Strip HTML tags from text before classification
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    # Auto-reply patterns (check first — these aren't human replies)
    auto_patterns = [
        "we have received your", "ticket has been created", "request received",
        "auto-reply", "automatic reply", "out of office", "ooo",
        "this is an automated", "do not reply", "no-reply", "noreply",
        "your request", "has been received", "currently experiencing",
        "visit our career site", "apply on our website", "apply online",
        "this mailbox is not monitored", "unsubscribe", "click here to apply",
        "auto response", "autoresponse",
        # Recruitment portal auto-replies
        "interested in career opportunities at",  # e.g. Capital One generic auto-reply
        "please visit our career", "please apply through",
        "apply for the suitable position",  # e.g. Infosys auto-reply
        "apply on our job portal",
    ]
    if any(p in text for p in auto_patterns):
        return "auto_reply"

    # Rejection patterns — comprehensive list for job outreach
    reject_patterns = [
        # Direct rejections
        "not hiring", "not currently hiring", "no open positions",
        "position has been filled", "role has been filled", "already filled",
        "no longer available", "no longer open",
        "not a good fit", "not the right fit", "not a match", "not the right match",
        "not suitable", "not aligned",
        # Short polite declines
        "we will pass", "will pass at the moment", "we'll pass",
        "going to pass", "have to pass", "i'll pass",
        "apologies. we will pass", "we are going to pass",
        # "Unfortunately" phrases
        "unfortunately", "regret to inform", "regret that",
        # Moving forward with others
        "moved forward with other", "moving forward with other",
        "decided to go with", "decided to move forward with",
        "chosen to proceed with", "selected another",
        "not moving forward", "won't be moving forward", "will not be moving forward",
        "not proceeding", "won't be proceeding", "will not be proceeding",
        "not able to move forward", "unable to move forward",
        "decided not to proceed", "decided not to move",
        "not be able to", "cannot proceed",
        # Experience mismatch
        "looking for more experience", "require more experience",
        "looking for 3", "looking for 4", "looking for 5",
        "looking for 6", "looking for 7", "looking for 8",
        "minimum of 5 year", "minimum of 3 year",
        "years of experience required",
        "overqualified", "underqualified", "under qualified", "over qualified",
        # Location mismatch
        "onsite only", "onsite role", "full time onsite", "in-office only",
        "no remote", "no visa", "no sponsorship", "visa sponsorship",
        "relocation required", "must be based in", "must be located",
        # Budget/timing
        "budget constraints", "hiring freeze", "on hold",
        "paused the search", "put on hold",
        # Polite declines
        "keep your resume on file", "keep your cv on file",
        "reach out if something", "future opportunities",
        "best of luck", "wish you the best", "good luck in your search",
        "all the best in your", "wishing you success",
        # Skill mismatch — only clear rejections, not "we are looking for X, do you have it?"
        "require someone with",
        "different skill set", "specific requirements",
        "not what we're looking for",
        # Generic decline phrases
        "thank you for your interest but",
        "appreciate your interest but",
        "appreciate you reaching out but",
        "thanks for reaching out but",
        "at this time we",
        "at this point we",
        "not in a position to",
    ]
    if any(p in text for p in reject_patterns):
        return "rejection"

    # Interest patterns — use word-boundary-aware matching to avoid false positives
    # e.g. "interested in career opportunities at Capital One?" is an auto-reply, not interest
    interest_patterns = [
        "interested", "relevant", "your background", "your experience",
        "would like to", "let's connect", "let's schedule", "let's chat",
        "send your cv", "send cv", "share your resume", "send your resume",
        "open to work", "join", "round",
        "interview", "phone screen", "technical assessment",
        "call", "discussion", "meet",
        "keep you posted", "will reach out", "get back to you",
        "impressive", "great fit", "perfect fit", "strong candidate",
        "like to learn more", "tell me more",
        "schedule a time", "book a call", "set up a call",
        "exciting", "love to chat", "would love to",
    ]
    if any(p in text for p in interest_patterns):
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


def _extract_email_body(msg):
    """Extract plain-text body from an email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="replace")
                break
            elif ct == "text/html" and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    # Strip HTML tags for a rough preview
                    raw = payload.decode("utf-8", errors="replace")
                    body = re.sub(r'<[^>]+>', ' ', raw)
                    body = re.sub(r'\s+', ' ', body).strip()
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            if msg.get_content_type() == "text/html":
                raw = payload.decode("utf-8", errors="replace")
                body = re.sub(r'<[^>]+>', ' ', raw)
                body = re.sub(r'\s+', ' ', body).strip()
            else:
                body = payload.decode("utf-8", errors="replace")
    return body


def _is_reply_after_sent(date_str, sent_at):
    """Check if an email date is after our sent_at timestamp. Returns True if after or if we can't determine."""
    try:
        from email.utils import parsedate_to_datetime
        reply_dt = parsedate_to_datetime(date_str)
        # Normalize to naive UTC for comparison
        if reply_dt.tzinfo is not None:
            import datetime as _dt
            reply_naive = reply_dt.astimezone(_dt.timezone.utc).replace(tzinfo=None)
        else:
            reply_naive = reply_dt
        # Parse sent_at (stored as ISO format in DB, naive UTC)
        sent_naive = datetime.fromisoformat(sent_at.replace("Z", "+00:00").replace("+00:00", "")) if sent_at else None
        if sent_naive and reply_naive < sent_naive:
            return False  # Reply is before we sent
    except Exception:
        pass
    return True  # Default: assume it's valid


def _imap_check_replies(since_date=None, limit=500, folders=None):
    """Connect to IMAP, search for replies to sent outreach emails.

    Args:
        since_date: Only search for emails received after this date (YYYY-MM-DD string).
                    Defaults to 14 days ago.
        limit: Max number of unreplied outreach emails to check (default 500).
        folders: List of IMAP folders to search. Defaults to INBOX + [Gmail]/All Mail.
    """
    conn = init_db()

    # Clean up stuck runs first (running for > 10 minutes = stuck)
    conn.execute(
        "UPDATE worker_runs SET finished_at=datetime('now'), status='failed' "
        "WHERE worker_type='imap_check' AND status='running' AND started_at < datetime('now', '-10 minutes')"
    )
    conn.commit()

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
        "AND eo.sent_at IS NOT NULL "
        "ORDER BY eo.sent_at DESC LIMIT ?",
        (limit,)
    ).fetchall()

    if not sent:
        conn.execute(
            "UPDATE worker_runs SET finished_at=datetime('now'), status='completed', succeeded=0, total=0, results=? WHERE id=?",
            ('{"replies_found": 0, "total_checked": 0, "note": "no unreplied emails"}', run_id)
        )
        conn.commit()
        conn.close()
        return 0

    # Build lookup: email -> list of outreach records
    email_lookup = {}
    earliest_sent = None
    for row in sent:
        addr = (row["recipient_email"] or "").lower().strip()
        if addr:
            email_lookup.setdefault(addr, []).append(row)
            if row["sent_at"] and (earliest_sent is None or row["sent_at"] < earliest_sent):
                earliest_sent = row["sent_at"]

    if not email_lookup:
        conn.close()
        return 0

    imap_user = IMAP_CONFIG["user"]
    imap_pass = IMAP_CONFIG["password"]

    if not imap_user or not imap_pass:
        raise ValueError("IMAP credentials not configured (SMTP_USER/SMTP_PASSWORD)")

    # Compute SINCE date for IMAP search (dramatically speeds up Gmail searches)
    if since_date:
        imap_since = since_date
    elif earliest_sent:
        # Use 1 day before earliest unreplied email
        try:
            dt = datetime.fromisoformat(earliest_sent[:10])
            dt = dt - timedelta(days=1)
            imap_since = dt.strftime("%d-%b-%Y")  # IMAP date format: 01-Mar-2026
        except Exception:
            dt = datetime.now() - timedelta(days=30)
            imap_since = dt.strftime("%d-%b-%Y")
    else:
        dt = datetime.now() - timedelta(days=14)
        imap_since = dt.strftime("%d-%b-%Y")

    # Folders to search — INBOX first, then All Mail for anything we missed
    if folders is None:
        folders = ["INBOX", "[Gmail]/All Mail"]

    # Connect to IMAP
    mail = imaplib.IMAP4_SSL(IMAP_CONFIG["host"], IMAP_CONFIG["port"], timeout=30)
    mail.login(imap_user, imap_pass)

    replies_found = 0
    total_checked = 0
    already_matched = set()  # Track outreach IDs already matched to avoid duplicates

    try:
        for folder in folders:
            try:
                status, _ = mail.select(folder, readonly=True)
                if status != "OK":
                    continue
            except Exception:
                continue

            # Search for emails FROM any of our outreach recipients
            for recipient_email, outreach_rows in email_lookup.items():
                # Skip if all outreach for this recipient already matched
                if all(o["id"] in already_matched for o in outreach_rows):
                    continue

                try:
                    # Search with SINCE filter for speed
                    safe_email = recipient_email.replace('"', '\\"')
                    status, data = mail.search(None, f'(FROM "{safe_email}" SINCE {imap_since})')
                    if status != "OK" or not data[0]:
                        continue

                    msg_ids = data[0].split()
                    # Check most recent messages first (last 5 per sender is enough)
                    for msg_id in reversed(msg_ids[-5:]):
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
                            body_full = _extract_email_body(msg)
                            body_preview = body_full[:500]

                            # Match to outreach records
                            for outreach in outreach_rows:
                                if outreach["id"] in already_matched:
                                    continue

                                outreach_subject = outreach["subject"] or ""

                                # Subject matching — relaxed to catch more replies
                                subj_lower = subject.lower().strip()
                                orig_lower = outreach_subject.lower().strip()
                                is_subject_match = (
                                    orig_lower and orig_lower in subj_lower  # original subject in reply
                                    or subj_lower.startswith("re:")  # any Re: from this sender
                                    or subj_lower.startswith("fw:")
                                    or subj_lower.startswith("fwd:")
                                )

                                # From address match (catches replies with changed subjects)
                                is_from_match = recipient_email in from_addr

                                if is_subject_match or is_from_match:
                                    # Verify reply came after we sent
                                    if not _is_reply_after_sent(date_str, outreach["sent_at"]):
                                        continue

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

                                    if lead and lead["stage"] in ("applied", "outreach") and reply_type != "auto_reply":
                                        new_stage = "rejected" if reply_type == "rejection" else "replied"
                                        conn.execute(
                                            "UPDATE pipeline_leads SET stage = ?, updated_at = datetime('now') WHERE id = ?",
                                            (new_stage, lead["id"])
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
                                    already_matched.add(outreach["id"])
                                    break  # Found reply for this outreach, move on

                        except Exception:
                            continue

                except Exception:
                    continue

        # ── Bounce Detection ──
        # Search for mailer-daemon / delivery failure notifications
        mail.select("INBOX", readonly=True)
        for search_query in [
            f'FROM "mailer-daemon" SINCE {imap_since}',
            f'SUBJECT "Address not found" SINCE {imap_since}',
            f'SUBJECT "Delivery Status Notification" SINCE {imap_since}',
            f'SUBJECT "Undeliverable" SINCE {imap_since}',
            f'SUBJECT "Mail delivery failed" SINCE {imap_since}',
        ]:
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
                        body = _extract_email_body(msg)

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
                                replies_found += 1
                                with _bounce_cache_lock:
                                    _bounced_domains_cache["loaded_at"] = 0
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
        ("completed", replies_found, total_checked,
         json.dumps({"replies_found": replies_found, "total_checked": total_checked, "recipients_scanned": len(email_lookup), "since": imap_since}),
         run_id)
    )
    conn.commit()
    conn.close()

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
                if found:
                    print(f"[IMAP] Check complete — {found} new replies/bounces detected")
            except Exception as e:
                print(f"[IMAP] Error during check: {e}")
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
        print("[IMAP] Polling stopped")


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


def deep_scan_replies(since_date=None):
    """Run a deep backfill scan for ALL unreplied emails.

    Searches from since_date (default: 01-Mar-2026) with no limit on emails checked.
    Use this to catch all missed replies from historical outreach.
    """
    if since_date is None:
        since_date = "01-Mar-2026"
    try:
        found = _imap_check_replies(
            since_date=since_date,
            limit=2000,  # Check all unreplied emails
            folders=["INBOX", "[Gmail]/All Mail", "[Gmail]/Important", "[Gmail]/Spam"],
        )
        return {
            "status": "ok",
            "replies_found": found,
            "last_checked": imap_worker_state.get("last_checked"),
            "scan_type": "deep_backfill",
            "since": since_date,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def reclassify_replies():
    """Re-run classification on all existing replies with updated keywords.

    Useful after adding new rejection/interest patterns.
    Returns count of replies whose type changed.
    """
    conn = init_db()
    replied = conn.execute(
        "SELECT id, reply_preview, subject FROM email_outreach WHERE status = 'replied' AND reply_preview IS NOT NULL"
    ).fetchall()

    changed = 0
    for row in replied:
        old_type = conn.execute("SELECT reply_type FROM email_outreach WHERE id = ?", (row["id"],)).fetchone()
        old_type = old_type["reply_type"] if old_type else None
        new_type = _classify_reply(row["reply_preview"], row["subject"])
        if new_type != old_type:
            conn.execute(
                "UPDATE email_outreach SET reply_type = ? WHERE id = ?",
                (new_type, row["id"])
            )
            # Update pipeline stage if rejection was missed
            if new_type == "rejection":
                lead = conn.execute(
                    "SELECT id, stage FROM pipeline_leads WHERE outreach_id = ?", (row["id"],)
                ).fetchone()
                if lead and lead["stage"] in ("applied", "replied", "outreach"):
                    conn.execute(
                        "UPDATE pipeline_leads SET stage = 'rejected', updated_at = datetime('now') WHERE id = ?",
                        (lead["id"],)
                    )
            changed += 1

    conn.commit()
    conn.close()
    return {"status": "ok", "total_replied": len(replied), "reclassified": changed}


def get_imap_status():
    """Get current IMAP worker status."""
    return dict(imap_worker_state)
