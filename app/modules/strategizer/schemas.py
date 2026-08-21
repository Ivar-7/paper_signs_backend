"""Schemas for the strategizer module."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AccountSummary(BaseModel):
    equity: float
    cash: float
    open_positions: int
    max_positions: int = 4


class StrategizerStats(BaseModel):
    total_scanned: int
    strong_buys: int
    buys: int
    watchlists: int
    exits: int
    best_opportunity_symbol: Optional[str] = None
    best_opportunity_score: float = 0.0


class MarketOpportunity(BaseModel):
    symbol: str
    signal_date: str
    close: Optional[float]
    change_24h_pct: float = 0.0
    sparkline: List[float] = []
    entry_high: Optional[float]
    exit_low: Optional[float]
    sma200: Optional[float]
    atr20: Optional[float]
    probability_score: float
    recommendation: str
    entry_signal: bool
    exit_signal: bool
    stop_loss: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    take_profit_3: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    distance_to_breakout_pct: float = 0.0
    sma200_clearance_pct: float = 0.0
    suggested_shares: Optional[int] = None
    suggested_cost: Optional[float] = None
    entry_reason: str = ""
    exit_reason: str = ""
    is_held: bool = False
    checklist: Dict[str, Any] = {}


class StrategizerScanResponse(BaseModel):
    account: AccountSummary
    stats: StrategizerStats
    markets: List[MarketOpportunity]


class SymbolItem(BaseModel):
    symbol: str
    name: Optional[str] = None
    is_tracked: bool = True


class AddSymbolRequest(BaseModel):
    symbol: str
