"""
Position sizing utilities          ATR-based risk sizing with capital cap.

These are pure functions; no I/O or state mutations.
"""

from __future__ import annotations

import math
from typing import Optional

from paper_signs_backend.app.strategy.constants import (
    ATR_MULTIPLIER,
    MAX_POSITION_PCT,
    RISK_PER_TRADE,
)


def calculate_shares(
    equity: float,
    close: float,
    atr: float,
    risk_per_trade: float = RISK_PER_TRADE,
    atr_multiplier: float = ATR_MULTIPLIER,
    max_position_pct: float = MAX_POSITION_PCT,
    available_cash: Optional[float] = None,
) -> tuple[int, float]:
    """
    Compute the number of shares to buy using ATR risk sizing.

    Returns (shares, cost) where:
      shares = min(risk-sized, capital-capped, cash-available)
      cost   = shares x close
    """
    if atr <= 0 or close <= 0 or equity <= 0:
        return 0, 0.0

    risk_dollars = equity * risk_per_trade
    stop_distance = atr_multiplier * atr
    risk_shares = math.floor(risk_dollars / stop_distance)

    capital_shares = math.floor(equity * max_position_pct / close)

    shares = min(risk_shares, capital_shares)

    if available_cash is not None and available_cash < shares * close:
        shares = math.floor(available_cash / close)

    if shares <= 0:
        return 0, 0.0

    return shares, round(shares * close, 2)


def atr_stop_price(
    entry_price: float,
    atr: float,
    atr_multiplier: float = ATR_MULTIPLIER,
) -> float:
    """
    Return the theoretical ATR stop level for reference only.
    NOTE: The strategy does NOT use a hard stop-loss; the 50-day low is the real exit.
    This is purely informational for display purposes.
    """
    return entry_price - (atr_multiplier * atr)
