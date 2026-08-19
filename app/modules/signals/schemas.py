"""Signals Pydantic schemas."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class SignalOut(BaseModel):
    id: int
    signal_date: date
    symbol: str
    close: Optional[float]
    entry_high: Optional[float]
    exit_low: Optional[float]
    sma200: Optional[float]
    atr20: Optional[float]
    entry_signal: bool
    exit_signal: bool
    suggested_shares: Optional[int]
    suggested_cost: Optional[float]

    model_config = {"from_attributes": True}