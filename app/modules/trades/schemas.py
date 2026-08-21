"""Trades Pydantic schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class TradeOut(BaseModel):
    id: int
    trade_date: date
    symbol: str
    action: str
    shares: int
    price: float
    cost: float
    pnl: Optional[float] = None
    broker_order_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TradeSummary(BaseModel):
    total_trades: int
    total_pnl: float
    wins: int
    losses: int
    win_rate: float
    profit_factor: Optional[float] = None
    avg_win: Optional[float] = None
    avg_loss: Optional[float] = None


class ExecuteTradeRequest(BaseModel):
    symbol: str
    action: str = Field(default="BUY", description="BUY or SELL")
    shares: Optional[int] = Field(default=None, description="Shares to execute. If None, auto-sizes with ATR.")
    price: Optional[float] = Field(default=None, description="Optional custom execution price override.")
    notes: Optional[str] = None


class ExecuteTradeResponse(BaseModel):
    success: bool
    symbol: str
    action: str
    shares: int
    filled_price: float
    cost: float
    pnl: Optional[float] = None
    message: str
    order_id: Optional[str] = None