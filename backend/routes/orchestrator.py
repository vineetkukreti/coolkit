"""Orchestrator routes — daily cycle management."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class OrchestratorRequest(BaseModel):
    max_applications: int = 500
    run_scrapers: bool = True


@router.post("/api/orchestrator/start")
def api_start_orchestrator(req: OrchestratorRequest):
    from services.orchestrator import start_daily_cycle
    return start_daily_cycle(
        max_applications=req.max_applications,
        run_scrapers=req.run_scrapers,
    )


@router.post("/api/orchestrator/stop")
def api_stop_orchestrator():
    from services.orchestrator import stop_daily_cycle
    return stop_daily_cycle()


@router.get("/api/orchestrator/status")
def api_orchestrator_status():
    from services.orchestrator import get_orchestrator_status
    return get_orchestrator_status()
