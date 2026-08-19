"""System router                    status and manual trigger endpoints."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from paper_signs_backend.app.config import get_settings
from paper_signs_backend.app.modules.system import service
from paper_signs_backend.app.modules.system.schemas import StatusResponse

router = APIRouter(tags=["system"])
_settings = get_settings()


@router.get("/api/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    """Return scheduler status and next run time."""
    return service.get_status(broker=_settings.broker, symbols=_settings.symbol_list)


@router.post("/api/run")
def trigger_run() -> Dict[str, Any]:
    """Manually trigger the daily strategy run."""
    return service.trigger_run()