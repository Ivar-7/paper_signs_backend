"""Portfolio Pydantic schemas."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class PositionOut(BaseModel):
    symbol: str
    shares: int
    avg_entry_price: float
    current_price: Optional[float]
    unrealized_pnl: Optional[float]
    entry_date: Optional[str]
    market_value: Optional[float] = None


class PortfolioOut(BaseModel):
    equity: float
    cash: float
    positions: List[PositionOut]
    snapshot_date: Optional[str] = None


class EquityPoint(BaseModel):
    date: str
    equity: float