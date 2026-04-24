"""Auto-apply API routes — start/stop/status for automated job applications."""

from fastapi import APIRouter
from pydantic import BaseModel

from db import init_db, get_today_quota, get_application_stats
from services.auto_apply import (
    start_auto_apply, stop_auto_apply, get_auto_apply_status,
)

router = APIRouter()


class AutoApplyRequest(BaseModel):
    max_applications: int = 500


@router.post("/api/auto-apply/start")
def api_start_auto_apply(req: AutoApplyRequest):
    result = start_auto_apply(max_applications=req.max_applications)
    if "error" in result:
        return {"status": "error", "message": result["error"]}
    return result


@router.post("/api/auto-apply/stop")
def api_stop_auto_apply():
    return stop_auto_apply()


@router.get("/api/auto-apply/status")
def api_auto_apply_status():
    return get_auto_apply_status()


@router.get("/api/auto-apply/quota")
def api_auto_apply_quota():
    conn = init_db()
    quota = get_today_quota(conn)
    stats = get_application_stats(conn)
    return {
        "quota": quota,
        "stats": stats,
    }
