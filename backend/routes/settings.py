"""Settings routes — profile, SMTP, Gemini, resume upload, test email."""

import os
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from config import PROFILE
from services.email_service import _send_email_smtp, SMTP_CONFIG

router = APIRouter()

# ───────────────────────────────────────────────
# Thread-local DB connection
# ───────────────────────────────────────────────
from db import init_db

_local = threading.local()


def _get_db():
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = init_db()
    return _local.conn


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
    experience_years: int = 2
    notice_period_days: int = 30
    resume_path: str = ""


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
def api_save_profile(req: ProfileUpdate):
    """Save profile to config.py and update in-memory PROFILE dict."""
    updates = req.model_dump(exclude_unset=True)
    for key, val in updates.items():
        if val is not None and val != "":
            PROFILE[key] = val

    # Write config.py
    config_path = Path("backend/config.py")
    lines = [
        '"""User profile config — edit your details here."""\n',
        "PROFILE = {\n",
    ]
    for k, v in PROFILE.items():
        if isinstance(v, str):
            lines.append(f'    "{k}": "{v}",\n')
        else:
            lines.append(f'    "{k}": {v},\n')
    lines.append("}\n")

    # Preserve RESUME_SKILLS and DEFAULTS from existing file
    existing = config_path.read_text()
    skills_start = existing.find("RESUME_SKILLS")
    if skills_start >= 0:
        lines.append("\n")
        lines.append(existing[skills_start:])

    config_path.write_text("".join(lines))
    return {"status": "ok", "message": "Profile saved"}


@router.post("/api/settings/smtp")
def api_save_smtp(req: SmtpUpdate):
    """Save SMTP settings to .env and update in-memory config."""
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
def api_save_gemini(req: GeminiUpdate):
    """Save Gemini API key to .env."""
    _update_env(GEMINI_API_KEY=req.api_key)
    os.environ["GEMINI_API_KEY"] = req.api_key
    return {"status": "ok", "message": "Gemini API key saved"}


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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/settings/upload-resume")
def api_upload_resume(file: UploadFile = File(...)):
    """Upload a resume PDF. Saves to project root and updates config.py."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    dest = Path("assets") / file.filename
    content = file.file.read()
    dest.write_bytes(content)

    # Update PROFILE in memory
    PROFILE["resume_path"] = str(dest)

    # Re-write config.py
    config_path = Path("backend/config.py")
    existing = config_path.read_text()
    skills_start = existing.find("RESUME_SKILLS")
    lines = [
        '"""User profile config — edit your details here."""\n',
        "PROFILE = {\n",
    ]
    for k, v in PROFILE.items():
        if isinstance(v, str):
            lines.append(f'    "{k}": "{v}",\n')
        else:
            lines.append(f'    "{k}": {v},\n')
    lines.append("}\n")
    if skills_start >= 0:
        lines.append("\n")
        lines.append(existing[skills_start:])
    config_path.write_text("".join(lines))

    size_kb = len(content) / 1024
    return {
        "status": "ok",
        "message": f"Resume uploaded: {file.filename} ({size_kb:.0f} KB)",
        "filename": file.filename,
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
