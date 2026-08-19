"""Compatibility shim                    re-exports from models/orm.py and models/database.py."""
from paper_signs_backend.app.models.orm import (
    Base, PortfolioSnapshot, Trade, Signal,
    BacktestResult, RobustnessResult, SchedulerRun,
)
from paper_signs_backend.app.models.database import engine, SessionLocal, init_db


def get_db():
    """Legacy dependency shim                    use app/dependencies/db.py for new code."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = [
    "Base", "PortfolioSnapshot", "Trade", "Signal",
    "BacktestResult", "RobustnessResult", "SchedulerRun",
    "engine", "SessionLocal", "init_db", "get_db",
]