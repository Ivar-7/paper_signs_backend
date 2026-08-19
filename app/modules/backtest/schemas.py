"""Backtest Pydantic schemas."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class BacktestResultOut(BaseModel):
    id: int
    period_name: str
    start_date: str
    end_date: str
    cagr: Optional[float]
    max_drawdown: Optional[float]
    sharpe: Optional[float]
    sortino: Optional[float]
    profit_factor: Optional[float]
    win_rate: Optional[float]
    avg_win: Optional[float]
    avg_loss: Optional[float]
    total_trades: Optional[int]
    avg_holding_days: Optional[float]
    final_equity: Optional[float]
    per_symbol_metrics: Optional[Dict[str, Any]]
    parameters: Optional[Dict[str, Any]]
    created_at: str

    model_config = {"from_attributes": True}


class RobustnessResultOut(BaseModel):
    id: int
    test_type: str
    test_label: str
    period_name: str
    cagr: Optional[float]
    max_drawdown: Optional[float]
    sharpe: Optional[float]
    profit_factor: Optional[float]
    total_trades: Optional[int]
    created_at: str