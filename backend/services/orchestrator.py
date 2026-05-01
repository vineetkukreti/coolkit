"""
Daily Orchestrator
------------------
Runs the full daily job application cycle:
  1. Scrape all sources (API first, then browser)
  2. Rank unapplied jobs by fit
  3. Auto-apply until quota exhausted
  4. Generate daily report

Can be triggered via API or cron.
"""

import threading
import time
from datetime import datetime

from db import init_db, get_unapplied_jobs, get_today_quota, quota_remaining, get_application_stats
from services.auto_apply import AutoApplyEngine, auto_apply_state, _apply_lock, _emit

# ─── Orchestrator State ──────────────────────────────────────────────────────

orchestrator_state = {
    "running": False,
    "status": "idle",  # idle | scraping | applying | done | error
    "started_at": None,
    "phase": None,
    "log": [],
}

_orch_lock = threading.Lock()
_orch_stop = threading.Event()


def _orch_emit(event: dict):
    with _orch_lock:
        orchestrator_state["log"].append({
            "time": datetime.now().isoformat(),
            **event,
        })
        if len(orchestrator_state["log"]) > 300:
            orchestrator_state["log"] = orchestrator_state["log"][-300:]


# ─── Daily Cycle ─────────────────────────────────────────────────────────────

def run_daily_cycle(max_applications: int = 500, run_scrapers: bool = True):
    """Full daily pipeline: Scrape → Rank → Apply → Report."""

    with _orch_lock:
        if orchestrator_state["running"]:
            return {"error": "Orchestrator already running"}
        orchestrator_state["running"] = True
        orchestrator_state["status"] = "starting"
        orchestrator_state["started_at"] = datetime.now().isoformat()
        orchestrator_state["log"] = []

    _orch_stop.clear()
    _orch_emit({"type": "info", "message": f"Daily cycle started (target: {max_applications})"})

    conn = init_db()

    try:
        # ── Phase 1: Run scrapers ──
        if run_scrapers:
            with _orch_lock:
                orchestrator_state["status"] = "scraping"
                orchestrator_state["phase"] = "scraping"

            _orch_emit({"type": "info", "message": "Phase 1: Running scrapers..."})
            _run_scraper_phase()

            if _orch_stop.is_set():
                _orch_emit({"type": "info", "message": "Stopped by user"})
                return

        # ── Phase 1.5: Smart scoring ──
        with _orch_lock:
            orchestrator_state["status"] = "scoring"
            orchestrator_state["phase"] = "scoring"

        _orch_emit({"type": "info", "message": "Phase 1.5: Smart-scoring unscored jobs..."})
        try:
            from services.smart_filter import score_all_unscored, filter_unapplied
            score_result = score_all_unscored(conn, limit=500)
            _orch_emit({"type": "info", "message": f"Smart scoring: {score_result.get('message', 'done')}"})
        except Exception as e:
            _orch_emit({"type": "error", "message": f"Smart scoring error (continuing): {str(e)[:200]}"})

        if _orch_stop.is_set():
            _orch_emit({"type": "info", "message": "Stopped by user"})
            return

        # ── Phase 2: Auto-apply (smart-filtered) ──
        with _orch_lock:
            orchestrator_state["status"] = "applying"
            orchestrator_state["phase"] = "applying"

        remaining = quota_remaining(conn)
        target = min(max_applications, remaining)
        _orch_emit({"type": "info", "message": f"Phase 2: Auto-applying to {target} smart-filtered jobs..."})

        # Use smart filter if available, fallback to original
        try:
            unapplied = filter_unapplied(conn, threshold=5.0, limit=target * 2)
            _orch_emit({"type": "info", "message": f"Smart filter: {len(unapplied)} jobs above threshold (score >= 5.0)"})
        except Exception:
            unapplied = get_unapplied_jobs(conn, limit=target * 2)
            _orch_emit({"type": "info", "message": f"Fallback: {len(unapplied)} unapplied jobs (no smart filter)"})

        if unapplied:
            from services.browser_service import browser_state
            page = browser_state.get("page")

            engine = AutoApplyEngine(conn, page=page)
            engine.run(max_applications=target)

        # ── Phase 3: Report ──
        with _orch_lock:
            orchestrator_state["status"] = "reporting"
            orchestrator_state["phase"] = "reporting"

        quota = get_today_quota(conn)
        stats = get_application_stats(conn)

        _orch_emit({
            "type": "report",
            "message": (
                f"Daily cycle complete. "
                f"Applied: {quota.get('applied', 0)}/{quota.get('target', 500)}, "
                f"Failed: {quota.get('failed', 0)}, "
                f"Skipped: {quota.get('skipped', 0)}, "
                f"Total all-time: {stats.get('total', 0)}"
            ),
        })

    except Exception as e:
        _orch_emit({"type": "error", "message": f"Orchestrator error: {str(e)[:300]}"})
        with _orch_lock:
            orchestrator_state["status"] = "error"
    finally:
        if conn:
            conn.close()
        with _orch_lock:
            if orchestrator_state["status"] not in ("error",):
                orchestrator_state["status"] = "done"
            orchestrator_state["running"] = False
            orchestrator_state["phase"] = None


def _run_scraper_phase():
    """Run all scrapers (API first, then browser if available)."""
    from services.scraper_service import _scraper_coordinator, scraper_state, _scraper_lock

    # Check if scraper is already running
    with _scraper_lock:
        if scraper_state["running"]:
            _orch_emit({"type": "info", "message": "Scraper already running, skipping scrape phase"})
            return

    # Run API scrapers (no browser needed)
    api_sources = ["remoteok", "himalayas", "hn"]
    _orch_emit({"type": "info", "message": f"Running API scrapers: {', '.join(api_sources)}"})

    try:
        _scraper_coordinator(max_posts=200, sources=api_sources)
    except Exception as e:
        _orch_emit({"type": "error", "message": f"API scraper error: {str(e)[:200]}"})

    # Run browser scrapers if browser is available
    from services.browser_service import browser_state
    if browser_state.get("running"):
        browser_sources = ["linkedin", "google", "wellfound", "yc"]
        _orch_emit({"type": "info", "message": f"Running browser scrapers: {', '.join(browser_sources)}"})
        try:
            _scraper_coordinator(max_posts=200, sources=browser_sources)
        except Exception as e:
            _orch_emit({"type": "error", "message": f"Browser scraper error: {str(e)[:200]}"})
    else:
        _orch_emit({"type": "info", "message": "Browser not running — skipping browser scrapers"})


# ─── Public API ──────────────────────────────────────────────────────────────

def start_daily_cycle(max_applications: int = 500, run_scrapers: bool = True):
    """Start the daily cycle in a background thread."""
    if orchestrator_state["running"]:
        return {"error": "Already running"}

    t = threading.Thread(
        target=run_daily_cycle,
        args=(max_applications, run_scrapers),
        daemon=True,
    )
    t.start()
    return {"status": "started", "target": max_applications}


def stop_daily_cycle():
    """Stop the orchestrator."""
    _orch_stop.set()
    from services.auto_apply import stop_auto_apply
    stop_auto_apply()
    return {"status": "stopping"}


def get_orchestrator_status() -> dict:
    """Get orchestrator state."""
    with _orch_lock:
        return {
            "running": orchestrator_state["running"],
            "status": orchestrator_state["status"],
            "phase": orchestrator_state["phase"],
            "started_at": orchestrator_state["started_at"],
            "log": orchestrator_state["log"][-100:],
        }
