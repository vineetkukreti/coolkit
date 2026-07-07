"""Scraper API routes."""

import threading
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db import init_db
from services.browser_service import browser_state
from services.scraper_service import (
    scraper_state, _scraper_lock, _scraper_coordinator,
)

router = APIRouter()

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


class ScraperStartRequest(BaseModel):
    max_posts: int = 200
    sources: list[str] = ["linkedin"]


@router.post("/api/scraper/start")
def api_start_scraper(req: ScraperStartRequest):
    from config_sources import GENERIC_HTML_SOURCES, GENERIC_API_SOURCES, CUSTOM_SOURCES
    api_only_sources = {"remoteok", "himalayas", "hn", "remotive", "wwr_rss", "workingnomads", "greenhouse", "lever", "ashby", "jobspy"}
    api_only_sources.update(GENERIC_HTML_SOURCES.keys())
    api_only_sources.update(GENERIC_API_SOURCES.keys())
    valid_sources = set(CUSTOM_SOURCES.keys()) | set(GENERIC_HTML_SOURCES.keys()) | set(GENERIC_API_SOURCES.keys())
    sources = [s for s in req.sources if s in valid_sources] or ["linkedin"]
    needs_browser = any(s not in api_only_sources for s in sources)
    if needs_browser and not browser_state.get("running"):
        raise HTTPException(status_code=400, detail="Browser not running. Start it from Settings first (API scrapers like RemoteOK, Himalayas, HN don't need it).")
    # Only reject sources that are already actively running (allow non-overlapping parallel starts)
    with _scraper_lock:
        active = scraper_state.get("active_sources", set())
        overlap = set(sources) & active
        if overlap:
            names = ", ".join(sorted(overlap))
            raise HTTPException(status_code=400, detail=f"Already scraping: {names}. You can start other sources in parallel.")
        sources = [s for s in sources if s not in active]  # filter out any overlap
        if not sources:
            return {"status": "ok", "message": "All requested sources already active"}
        scraper_state["running"] = True
        scraper_state["status"] = "running"
    from worker_ctx import current_uid
    threading.Thread(
        target=_scraper_coordinator,
        args=(req.max_posts, sources, current_uid()),
        daemon=True,
    ).start()
    source_names = ", ".join(s.capitalize() for s in sources)
    return {"status": "started", "message": f"Scraping {source_names} in parallel for up to {req.max_posts} posts..."}


@router.post("/api/scraper/stop")
def api_stop_scraper(source: str = None):
    """Stop scraping. Pass ?source=linkedin to stop one source, or omit to stop all."""
    with _scraper_lock:
        if source:
            # Stop a specific source
            scraper_state["active_sources"].discard(source)
            src = scraper_state.get("sources", {}).get(source)
            if src and src["status"] in ("waiting", "running"):
                src["status"] = "stopped"
            if not scraper_state["active_sources"]:
                scraper_state["running"] = False
                scraper_state["status"] = "idle"
                scraper_state["started_at"] = None
        else:
            # Stop all
            scraper_state["running"] = False
            scraper_state["status"] = "idle"
            scraper_state["active_sources"].clear()
            scraper_state["started_at"] = None
            for s in scraper_state.get("sources", {}).values():
                if s["status"] in ("waiting", "running"):
                    s["status"] = "stopped"
    return {"status": "stopped", "stopped": source or "all"}


@router.get("/api/scraper/status")
def api_scraper_status():
    with _scraper_lock:
        sources_data = {}
        for name, state in scraper_state.get("sources", {}).items():
            sources_data[name] = {
                "status": state["status"],
                "log": state["log"],
                "log_count": len(state["log"]),
                "progress": state["progress"],
            }
        return {
            "running": scraper_state["running"],
            "status": scraper_state["status"],
            "started_at": scraper_state.get("started_at"),
            "sources": sources_data,
            "active_sources": list(scraper_state.get("active_sources", set())),
        }


@router.get("/api/scraper/sources")
def api_get_sources():
    """Get all available scraper sources grouped by category."""
    from config_sources import get_all_sources, SOURCE_GROUPS, get_source_count
    all_sources = get_all_sources()

    # Build grouped response
    groups = {}
    for key, src in all_sources.items():
        grp = src.get("group", "other")
        if grp not in groups:
            grp_cfg = SOURCE_GROUPS.get(grp, {"label": grp.title(), "icon": "📋", "order": 99})
            groups[grp] = {"label": grp_cfg["label"], "icon": grp_cfg["icon"], "order": grp_cfg["order"], "sources": []}
        groups[grp]["sources"].append({"key": key, "label": src["label"], "type": src.get("type", "custom")})

    # Sort groups by order
    sorted_groups = sorted(groups.items(), key=lambda x: x[1]["order"])

    return {
        "total": get_source_count(),
        "groups": [{"key": k, **v} for k, v in sorted_groups],
    }
