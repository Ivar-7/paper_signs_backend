"""Trades Pydantic schemas."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class TradeOut(BaseModel):
    id: int
    trade_date: date
    symbol: str
    action: str
    shares: int
    price: float
    cost: float
    pnl: Optional[float]
    broker_order_id: Optional[str]

    model_config = {"from_attributes": True}


class TradeSummary(BaseModel):
    total_trades: int
    total_pnl: float
    wins: int
    losses: int
    win_rate: float