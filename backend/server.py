#!/usr/bin/env python3
"""
FastAPI backend for Healthcare AI Job Applier.

Slim entry point — all logic lives in routes/ and services/.
"""

import os
import sys
import logging
import traceback
from pathlib import Path
from datetime import datetime
from collections import deque

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Project root is one level up from backend/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, str(_PROJECT_ROOT / "backend"))
load_dotenv()

# ───────────────────────────────────────────────
# Logging setup — file + in-memory ring buffer
# ───────────────────────────────────────────────

LOG_DIR = _PROJECT_ROOT / "data"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "server.log"

# Ring buffer for last 500 log entries (viewable via API)
_log_buffer = deque(maxlen=500)


class BufferHandler(logging.Handler):
    """Logging handler that stores entries in an in-memory ring buffer."""
    def emit(self, record):
        entry = {
            "time": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": self.format(record),
        }
        if record.exc_info and record.exc_info[1]:
            entry["traceback"] = traceback.format_exception(*record.exc_info)
        _log_buffer.append(entry)


# Configure root logger
_fmt = logging.Formatter("[%(asctime)s] %(levelname)-7s %(name)s — %(message)s", datefmt="%H:%M:%S")

# File handler
_fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(_fmt)

# Console handler
_ch = logging.StreamHandler()
_ch.setLevel(logging.INFO)
_ch.setFormatter(_fmt)

# Buffer handler
_bh = BufferHandler()
_bh.setLevel(logging.DEBUG)
_bh.setFormatter(_fmt)

logging.basicConfig(level=logging.DEBUG, handlers=[_fh, _ch, _bh])

# Reduce noise from third-party libs
for noisy in ["urllib3", "httpcore", "httpx", "watchfiles", "multipart"]:
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger("careerkit")
logger.info("CareerKit server starting...")

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
# Global exception handler — catch & log all 500s
# ───────────────────────────────────────────────

@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(exc), "path": request.url.path},
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": str(exc), "path": request.url.path},
    )


# ───────────────────────────────────────────────
# Log viewer API — see errors from the UI
# ───────────────────────────────────────────────

@app.get("/api/logs")
def api_get_logs(level: str = "", limit: int = 100, search: str = ""):
    """Get recent server logs from the in-memory buffer.

    Query params:
      level: filter by level (ERROR, WARNING, INFO, DEBUG)
      limit: max entries to return (default 100)
      search: text search in log messages
    """
    entries = list(_log_buffer)
    if level:
        entries = [e for e in entries if e["level"] == level.upper()]
    if search:
        search_lower = search.lower()
        entries = [e for e in entries if search_lower in e["message"].lower()]
    # Most recent first
    entries = list(reversed(entries[-limit:]))
    return {
        "logs": entries,
        "total": len(entries),
        "buffer_size": len(_log_buffer),
        "log_file": str(LOG_FILE),
    }


@app.get("/api/logs/errors")
def api_get_errors(limit: int = 50):
    """Get only ERROR-level logs — quick view of what's broken."""
    entries = [e for e in _log_buffer if e["level"] == "ERROR"]
    entries = list(reversed(entries[-limit:]))
    return {"errors": entries, "total": len(entries)}


@app.get("/api/logs/file")
def api_get_log_file(lines: int = 200):
    """Read last N lines from the log file on disk."""
    try:
        with open(str(LOG_FILE), "r") as f:
            all_lines = f.readlines()
        tail = all_lines[-lines:]
        return {"lines": [l.rstrip() for l in tail], "total_lines": len(all_lines), "file": str(LOG_FILE)}
    except FileNotFoundError:
        return {"lines": [], "total_lines": 0, "file": str(LOG_FILE), "error": "Log file not found"}


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
