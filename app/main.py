"""Application entry point - creation, middleware, routers, exception handlers."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from paper_signs_backend.app.config import get_settings
from paper_signs_backend.app.exceptions import register_exception_handlers
from paper_signs_backend.app.models.database import init_db
from paper_signs_backend.app.modules.portfolio.router import router as portfolio_router
from paper_signs_backend.app.modules.signals.router import router as signals_router
from paper_signs_backend.app.modules.strategizer.router import router as strategizer_router
from paper_signs_backend.app.modules.system.router import router as system_router
from paper_signs_backend.app.modules.system import service as system_service
from paper_signs_backend.app.modules.trades.router import router as trades_router
from paper_signs_backend.app.scheduler import run_daily_strategy

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler = BackgroundScheduler(timezone="UTC")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB, start scheduler. Shutdown: stop scheduler."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("PaperSigns Strategizer starting up")
    init_db()

    cron_parts = settings.schedule_cron.split()
    _scheduler.add_job(
        run_daily_strategy,
        trigger=CronTrigger(
            minute=cron_parts[0],
            hour=cron_parts[1],
            day=cron_parts[2],
            month=cron_parts[3],
            day_of_week=cron_parts[4],
            timezone="UTC",
        ),
        id="daily_strategy",
        name="Daily Donchian Strategy Run",
        replace_existing=True,
    )
    _scheduler.start()
    system_service.set_scheduler(_scheduler)
    logger.info("Scheduler background service initialized")

    yield

    _scheduler.shutdown(wait=False)
    logger.info("PaperSigns Strategizer shutting down")


app = FastAPI(
    title="PaperSigns Strategizer",
    description="Automated Paper Trading Strategizer (Donchian 100/50 + SMA200 + ATR20)",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(system_router)
app.include_router(strategizer_router)
app.include_router(portfolio_router)
app.include_router(trades_router)
app.include_router(signals_router)