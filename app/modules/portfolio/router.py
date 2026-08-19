"""Portfolio router — HTTP concerns only."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from paper_signs_backend.app.dependencies.broker import get_broker_dep
from paper_signs_backend.app.dependencies.db import get_db
from paper_signs_backend.app.broker.base import BaseBroker
from paper_signs_backend.app.modules.portfolio import service
from paper_signs_backend.app.modules.portfolio.schemas import EquityPoint, PortfolioOut

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/", response_model=PortfolioOut)
def get_portfolio(broker: BaseBroker = Depends(get_broker_dep)) -> PortfolioOut:
    """Return live portfolio state from the broker."""
    return service.get_live_portfolio(broker)


@router.get("/history", response_model=List[EquityPoint])
def get_equity_history(
    limit: int = 365,
    db: Session = Depends(get_db),
) -> List[EquityPoint]:
    """Return historical portfolio equity curve."""
    return service.get_equity_history(db, limit=limit)


@router.get("/snapshots")
def get_snapshots(
    limit: int = 30,
    db: Session = Depends(get_db),
):
    """Return raw portfolio snapshots with positions detail."""
    return service.get_snapshots(db, limit=limit)