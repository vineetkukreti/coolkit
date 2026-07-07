"""Settings routes — profile, SMTP, Gemini, resume upload, test email."""

import json
import os
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from pydantic import BaseModel

from config import PROFILE
from services.email_service import _send_email_smtp, SMTP_CONFIG

router = APIRouter()

# ───────────────────────────────────────────────
# Settings token protection
# ───────────────────────────────────────────────

SETTINGS_TOKEN = os.getenv("SETTINGS_TOKEN", "")


def _check_settings_token(request: Request):
    """If SETTINGS_TOKEN is set, require it as X-Settings-Token header."""
    if not SETTINGS_TOKEN:
        return  # Local dev — no protection needed
    token = request.headers.get("X-Settings-Token", "")
    if token != SETTINGS_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid or missing settings token")


# ───────────────────────────────────────────────
# Thread-local DB connection
# ───────────────────────────────────────────────
from db import init_db

_local = threading.local()


def _get_db():
    # Honor an explicitly-set connection (used directly by tests).
    override = getattr(_local, 'conn', None)
    if override is not None:
        return override
    # Otherwise keep one connection per user PER THREAD. Thread-local keeps each
    # connection confined to one thread (SQLite-safe); keying by user id stops a
    # pooled thread from serving user B with the connection it opened for user A.
    from db import current_user_id
    uid = current_user_id.get()
    cache = getattr(_local, 'by_user', None)
    if cache is None:
        cache = _local.by_user = {}
    conn = cache.get(uid)
    if conn is None:
        conn = cache[uid] = init_db()
    return conn


# ───────────────────────────────────────────────
# .env helpers
# ───────────────────────────────────────────────

ENV_PATH = Path("config/.env")


def _read_env() -> dict:
    """Read .env as key-value dict."""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _write_env(env: dict):
    """Write dict back to .env file."""
    lines = []
    for k, v in env.items():
        lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(lines) + "\n")


def _update_env(**kwargs):
    """Update specific keys in .env, preserving others."""
    env = _read_env()
    env.update(kwargs)
    _write_env(env)


# ───────────────────────────────────────────────
# Pydantic models
# ───────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""
    location: str = ""
    current_title: str = ""
    employer: str = ""
    employer_domain: str = ""
    experience_years: int = 0
    notice_period_days: int = 30
    resume_path: str = ""
    skills_summary: str = ""
    education: str = ""
    education_level: str = "Bachelor's Degree"
    certifications: str = "None"
    projects: list = []
    achievements: list = []
    desired_salary: int = 0
    current_salary: int = 0
    require_visa: str = "No"
    us_citizenship: str = "Not Applicable"
    willing_to_relocate: str = "Yes"
    previously_worked_here: str = "No"
    gender: str = "Decline to self-identify"
    ethnicity: str = "Decline to self-identify"
    disability_status: str = "I don't wish to answer"
    veteran_status: str = "I am not a protected veteran"


class SmtpUpdate(BaseModel):
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_email: str = ""
    from_name: str = ""


class GeminiUpdate(BaseModel):
    api_key: str


# ───────────────────────────────────────────────
# Endpoints
# ───────────────────────────────────────────────

@router.get("/api/profile")
def get_profile():
    return PROFILE


@router.get("/api/settings/all")
def api_get_all_settings():
    """Get all configurable settings in one call."""
    env = _read_env()
    return {
        "profile": PROFILE,
        "smtp": {
            "smtp_host": env.get("SMTP_HOST", "smtp.gmail.com"),
            "smtp_port": int(env.get("SMTP_PORT", "587")),
            "smtp_user": env.get("SMTP_USER", ""),
            "smtp_password_set": bool(env.get("SMTP_PASSWORD", "")),
            "from_email": env.get("FROM_EMAIL", ""),
            "from_name": env.get("FROM_NAME", ""),
        },
        "gemini": {
            "api_key_set": bool(env.get("GEMINI_API_KEY", "")),
            "api_key_preview": (env.get("GEMINI_API_KEY", "")[:8] + "...") if env.get("GEMINI_API_KEY") else "",
        },
        "imap": {
            "imap_host": env.get("IMAP_HOST", "imap.gmail.com"),
            "imap_port": env.get("IMAP_PORT", "993"),
            "imap_configured": bool(env.get("SMTP_USER") and env.get("SMTP_PASSWORD")),
        },
    }


@router.post("/api/settings/profile")
def api_save_profile(req: ProfileUpdate, request: Request):
    """Save profile to config/profile.json and update in-memory PROFILE dict."""
    _check_settings_token(request)
    updates = req.model_dump(exclude_unset=True)
    for key, val in updates.items():
        if val is not None:
            PROFILE[key] = val

    # Auto-derive first_name and last_name from name
    if "name" in updates and PROFILE.get("name"):
        parts = PROFILE["name"].strip().split()
        PROFILE["first_name"] = parts[0]
        PROFILE["last_name"] = parts[-1] if len(parts) > 1 else ""

    # Write to JSON file (safe — no code execution)
    profile_path = Path("config/profile.json")
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(json.dumps(PROFILE, indent=2))
    return {"status": "ok", "message": "Profile saved"}


@router.post("/api/settings/smtp")
def api_save_smtp(req: SmtpUpdate, request: Request):
    """Save SMTP settings to .env and update in-memory config."""
    _check_settings_token(request)
    update = {
        "SMTP_HOST": req.smtp_host,
        "SMTP_PORT": str(req.smtp_port),
        "SMTP_USER": req.smtp_user,
        "FROM_EMAIL": req.from_email,
        "FROM_NAME": req.from_name,
    }
    if req.smtp_password:
        update["SMTP_PASSWORD"] = req.smtp_password

    _update_env(**update)

    # Update in-memory
    SMTP_CONFIG["host"] = req.smtp_host
    SMTP_CONFIG["port"] = req.smtp_port
    SMTP_CONFIG["user"] = req.smtp_user
    SMTP_CONFIG["from_email"] = req.from_email
    SMTP_CONFIG["from_name"] = req.from_name
    if req.smtp_password:
        SMTP_CONFIG["password"] = req.smtp_password

    return {"status": "ok", "message": "SMTP config saved"}


@router.post("/api/settings/gemini")
def api_save_gemini(req: GeminiUpdate, request: Request):
    """Save Gemini API key to .env."""
    _check_settings_token(request)
    _update_env(GEMINI_API_KEY=req.api_key)
    os.environ["GEMINI_API_KEY"] = req.api_key
    return {"status": "ok", "message": "Gemini API key saved"}


@router.get("/api/settings/search-config")
def api_get_search_config():
    """Get current search configuration."""
    from config import (
        TARGET_ROLES, DOMAIN_KEYWORDS, RESUME_SKILLS, ACTIVE_REGIONS, DEFAULTS, REGIONS,
    )
    return {
        "target_roles": TARGET_ROLES,
        "domain_keywords": DOMAIN_KEYWORDS,
        "resume_skills": RESUME_SKILLS,
        "active_regions": ACTIVE_REGIONS,
        "available_regions": list(REGIONS.keys()),
        "default_location": DEFAULTS.get("location", ""),
        "max_jobs": DEFAULTS.get("max_jobs", 25),
        "mode": DEFAULTS.get("mode", "semi"),
    }


@router.post("/api/settings/search-config")
def api_save_search_config(req: dict, request: Request):
    """Save search configuration to config/search_config.json and update in-memory."""
    _check_settings_token(request)
    import config as cfg

    config_data = {}
    if "target_roles" in req:
        config_data["target_roles"] = req["target_roles"]
        cfg.TARGET_ROLES.clear()
        cfg.TARGET_ROLES.extend(req["target_roles"])
    if "domain_keywords" in req:
        config_data["domain_keywords"] = req["domain_keywords"]
        cfg.DOMAIN_KEYWORDS.clear()
        cfg.DOMAIN_KEYWORDS.extend(req["domain_keywords"])
    if "resume_skills" in req:
        config_data["resume_skills"] = req["resume_skills"]
        cfg.RESUME_SKILLS.clear()
        cfg.RESUME_SKILLS.update(req["resume_skills"])
    if "active_regions" in req:
        config_data["active_regions"] = req["active_regions"]
        cfg.ACTIVE_REGIONS.clear()
        cfg.ACTIVE_REGIONS.extend(req["active_regions"])
    if "default_location" in req:
        config_data["default_location"] = req["default_location"]
        cfg.DEFAULTS["location"] = req["default_location"]
    if "max_jobs" in req:
        config_data["max_jobs"] = req["max_jobs"]
        cfg.DEFAULTS["max_jobs"] = req["max_jobs"]
    if "mode" in req:
        config_data["mode"] = req["mode"]
        cfg.DEFAULTS["mode"] = req["mode"]

    # Merge with existing config and save
    existing = cfg._load_search_config()
    existing.update(config_data)
    cfg._save_search_config(existing)

    return {"status": "ok", "message": "Search config saved"}


@router.post("/api/settings/test-email")
def api_test_email():
    """Send a test email to verify SMTP config works."""
    if not SMTP_CONFIG["password"]:
        raise HTTPException(status_code=400, detail="SMTP password not configured")
    try:
        _send_email_smtp(
            SMTP_CONFIG["from_email"],
            "CareerKit — SMTP Test",
            "This is a test email from CareerKit.\n\nYour SMTP configuration is working correctly.\n\nYou can now send cold outreach emails from the Email tab.",
        )
        return {"status": "ok", "message": f"Test email sent to {SMTP_CONFIG['from_email']}"}
    except Exception as e:
        print(f"Error in /api/settings/test-email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test email. Check SMTP configuration.")


@router.post("/api/settings/upload-resume")
def api_upload_resume(file: UploadFile = File(...)):
    """Upload a resume PDF. Saves to assets/ and updates profile."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # Sanitize filename to prevent path traversal
    safe_filename = Path(file.filename).name
    dest = Path("assets") / safe_filename
    content = file.file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Max 10MB.")
    dest.write_bytes(content)

    # Update PROFILE in memory and persist to JSON
    PROFILE["resume_path"] = str(dest)
    profile_path = Path("config/profile.json")
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(json.dumps(PROFILE, indent=2))

    size_kb = len(content) / 1024
    return {
        "status": "ok",
        "message": f"Resume uploaded: {safe_filename} ({size_kb:.0f} KB)",
        "filename": safe_filename,
        "path": str(dest),
    }


@router.get("/api/settings/resume-status")
def api_resume_status():
    """Check if resume file exists."""
    path = Path(PROFILE.get("resume_path", ""))
    exists = path.exists()
    return {
        "exists": exists,
        "filename": path.name if exists else None,
        "path": str(path) if exists else None,
        "size_kb": round(path.stat().st_size / 1024) if exists else 0,
    }
