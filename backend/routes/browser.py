"""Browser control routes — start/stop/login Playwright browser."""

import traceback

from fastapi import APIRouter, HTTPException

from services.browser_service import (
    browser_state,
    _run_on_browser_thread,
    _do_start_browser,
    _do_open_login,
    _do_check_login,
    _do_stop_browser,
    _stop_browser,
)

router = APIRouter()


@router.post("/api/browser/start")
def start_browser():
    """Launch browser and automatically navigate to LinkedIn login."""
    if browser_state["running"]:
        return {"status": "already_running"}
    try:
        browser_state["status"] = "starting"
        _run_on_browser_thread(_do_start_browser)
        return {"status": "ready", "message": "Browser launched with LinkedIn login page."}
    except Exception as e:
        traceback.print_exc()
        browser_state["status"] = "error"
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/browser/login")
def open_login():
    """Navigate to LinkedIn login page."""
    if not browser_state["running"]:
        raise HTTPException(status_code=400, detail="Browser not running. Start it first.")
    try:
        _run_on_browser_thread(_do_open_login)
        return {"status": "ok", "message": "LinkedIn login page opened."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open login page: {str(e)[:200]}")


@router.post("/api/browser/check-login")
def check_login():
    """Check if user is logged into LinkedIn."""
    if not browser_state["running"]:
        return {"logged_in": False}
    try:
        is_logged = _run_on_browser_thread(_do_check_login, timeout=20)
        return {"logged_in": is_logged}
    except Exception:
        return {"logged_in": False}


@router.post("/api/browser/stop")
def stop_browser():
    """Close browser."""
    try:
        _run_on_browser_thread(_do_stop_browser, timeout=10)
    except Exception:
        _stop_browser()  # fallback: force-clean state
    return {"status": "stopped"}


@router.get("/api/browser/status")
def browser_status():
    return {
        "status": browser_state["status"],
        "running": browser_state["running"],
        "logged_in": browser_state["logged_in"],
    }
