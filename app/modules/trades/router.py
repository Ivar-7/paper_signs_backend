"""Trades router                    HTTP concerns only."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from paper_signs_backend.app.dependencies.db import get_db
from paper_signs_backend.app.modules.trades import service
from paper_signs_backend.app.modules.trades.schemas import TradeOut, TradeSummary

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.get("/", response_model=List[TradeOut])
def get_trades(
    symbol: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db),
) -> List[TradeOut]:
    """Return paginated trade history."""
    return service.get_trades(db, symbol=symbol, action=action, limit=limit, offset=offset)


@router.get("/summary", response_model=TradeSummary)
def get_trade_summary(db: Session = Depends(get_db)) -> TradeSummary:
    """Return aggregate trade statistics."""
    return service.get_summary(db)