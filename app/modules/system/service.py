"""System service — scheduler access and strategy trigger."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler

from paper_signs_backend.app.modules.system.schemas import StatusResponse

logger = logging.getLogger(__name__)

# Injected at startup by main.py
_scheduler: Optional[BackgroundScheduler] = None


def set_scheduler(scheduler: BackgroundScheduler) -> None:
    """Register the application scheduler with this service."""
    global _scheduler
    _scheduler = scheduler


def get_status(broker: str, symbols: list) -> StatusResponse:
    """Return current scheduler and system status."""
    job = _scheduler.get_job("daily_strategy") if _scheduler else None
    return StatusResponse(
        status="running",
        scheduler_running=_scheduler.running if _scheduler else False,
        next_run=str(job.next_run_time) if job else None,
        broker=broker,
        symbols=symbols,
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
    )


def trigger_run() -> Dict[str, Any]:
    """Manually execute the daily strategy cycle."""
    from paper_signs_backend.app.scheduler import run_daily_strategy
    logger.info("Manual strategy run triggered via API")
    return run_daily_strategy(triggered_by="api")