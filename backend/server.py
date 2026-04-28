#!/usr/bin/env python3
"""
FastAPI backend for Healthcare AI Job Applier.

Slim entry point — all logic lives in routes/ and services/.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Project root is one level up from backend/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, str(_PROJECT_ROOT / "backend"))
load_dotenv()

# ───────────────────────────────────────────────
# App
# ───────────────────────────────────────────────

app = FastAPI(title="CareerKit")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000", "http://127.0.0.1:5173", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ───────────────────────────────────────────────
# Startup config validation
# ───────────────────────────────────────────────
import os as _os
_missing = []
if not _os.getenv("SMTP_USER"): _missing.append("SMTP_USER")
if not _os.getenv("SMTP_PASSWORD"): _missing.append("SMTP_PASSWORD")
if _missing:
    print(f"[WARN] Missing env vars: {', '.join(_missing)} — email features disabled")
if not _os.getenv("GEMINI_API_KEY"):
    print(f"[WARN] GEMINI_API_KEY not set — AI email generation will fail")

# ───────────────────────────────────────────────
# Register all route modules
# ───────────────────────────────────────────────

from routes.jobs import router as jobs_router
from routes.browser import router as browser_router
from routes.posts import router as posts_router
from routes.email import router as email_router
from routes.pipeline import router as pipeline_router
from routes.scraper import router as scraper_router
from routes.leads import router as leads_router
from routes.settings import router as settings_router
from routes.tools import router as tools_router
from routes.auto_apply import router as auto_apply_router
from routes.skills_intel import router as skills_intel_router
from routes.orchestrator import router as orchestrator_router

app.include_router(jobs_router)
app.include_router(browser_router)
app.include_router(posts_router)
app.include_router(email_router)
app.include_router(pipeline_router)
app.include_router(scraper_router)
app.include_router(leads_router)
app.include_router(settings_router)
app.include_router(tools_router)
app.include_router(auto_apply_router)
app.include_router(skills_intel_router)
app.include_router(orchestrator_router)

# ───────────────────────────────────────────────
# Auto-start IMAP reply polling on startup
# ───────────────────────────────────────────────

@app.on_event("startup")
def _start_imap_polling():
    """Start IMAP reply detection polling when server starts."""
    try:
        from services.email_service import start_imap_polling
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASSWORD", "")
        if smtp_user and smtp_pass:
            start_imap_polling(interval_minutes=5)
            print(f"[IMAP] Reply detection started — polling every 5 minutes")
        else:
            print("[IMAP] Skipped — no SMTP credentials configured")
    except Exception as e:
        print(f"[IMAP] Failed to start: {e}")

# ───────────────────────────────────────────────
# Graceful shutdown for background workers
# ───────────────────────────────────────────────

@app.on_event("shutdown")
def shutdown_event():
    from services.scraper_service import scraper_state
    from services.auto_apply import stop_auto_apply
    from services.email_service import stop_imap_polling, stop_followup_worker

    # Signal all workers to stop
    scraper_state["running"] = False
    try:
        stop_auto_apply()
    except:
        pass
    try:
        stop_imap_polling()
    except:
        pass
    try:
        stop_followup_worker()
    except:
        pass

# ───────────────────────────────────────────────
# Serve frontend (must be last — catches all paths)
# ───────────────────────────────────────────────

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
