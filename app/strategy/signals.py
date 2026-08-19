"""
Signal generation          derives entry/exit signals from indicator columns.

Signals are generated using information available at the PREVIOUS close.
They are acted upon at the NEXT open to avoid look-ahead bias.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from paper_signs_backend.app.strategy.constants import (
    ATR_LENGTH,
    ATR_MULTIPLIER,
    ENTRY_LOOKBACK,
    EXIT_LOOKBACK,
    MAX_POSITION_PCT,
    MAX_POSITIONS,
    RISK_PER_TRADE,
    SMA_LENGTH,
)
from paper_signs_backend.app.strategy.indicators import add_all_indicators


@dataclass
class SymbolSignal:
    symbol: str
    signal_date: str
    close: Optional[float]
    entry_high: Optional[float]
    exit_low: Optional[float]
    sma200: Optional[float]
    atr20: Optional[float]
    entry_signal: bool
    exit_signal: bool
    suggested_shares: Optional[int] = None
    suggested_cost: Optional[float] = None
    entry_reason: str = ""
    exit_reason: str = ""


def _safe_float(val) -> Optional[float]:
    """Convert numpy/pandas scalar to Python float, returning None on NaN."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if (np.isnan(f) or np.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def generate_signal(
    symbol: str,
    df: pd.DataFrame,
    current_equity: float,
    already_held: bool,
    open_position_count: int,
    entry_lookback: int = ENTRY_LOOKBACK,
    exit_lookback: int = EXIT_LOOKBACK,
    sma_length: int = SMA_LENGTH,
    atr_length: int = ATR_LENGTH,
    atr_multiplier: float = ATR_MULTIPLIER,
    risk_per_trade: float = RISK_PER_TRADE,
    max_positions: int = MAX_POSITIONS,
    max_position_pct: float = MAX_POSITION_PCT,
) -> Optional[SymbolSignal]:
    """
    Compute the signal for a single symbol given its OHLCV DataFrame.

    Uses the last row (today's close) to assess whether conditions are met.
    Returns None if insufficient data.
    """
    min_rows = max(sma_length, entry_lookback) + 10
    if len(df) < min_rows:
        return None

    df = add_all_indicators(
        df,
        sma_length=sma_length,
        entry_lookback=entry_lookback,
        exit_lookback=exit_lookback,
        atr_length=atr_length,
    )

    row = df.iloc[-1]
    signal_date = str(df.index[-1].date())

    close = _safe_float(row["Close"])
    entry_high = _safe_float(row.get("EntryHigh"))
    exit_low = _safe_float(row.get("ExitLow"))
    sma200 = _safe_float(row.get(f"SMA{sma_length}"))
    atr20 = _safe_float(row.get(f"ATR{atr_length}"))

    if close is None or sma200 is None or entry_high is None or exit_low is None:
        return None

    # -- Entry conditions -----------------------------------
    entry_signal = (
        not already_held
        and open_position_count < max_positions
        and close > entry_high
        and close > sma200
        and atr20 is not None
    )

    entry_reason_parts = []
    if close > entry_high:
        entry_reason_parts.append(f"Close {close:.2f} > {entry_lookback}d High {entry_high:.2f}")
    if close > sma200:
        entry_reason_parts.append(f"> SMA{sma_length} {sma200:.2f}")
    entry_reason = " | ".join(entry_reason_parts) if entry_signal else ""

    # -- Exit conditions ------------------------------------
    exit_signal = already_held and (close < exit_low or close < sma200)

    exit_reason_parts = []
    if already_held:
        if close < exit_low:
            exit_reason_parts.append(f"Close {close:.2f} < {exit_lookback}d Low {exit_low:.2f}")
        if close < sma200:
            exit_reason_parts.append(f"< SMA{sma_length} {sma200:.2f}")
    exit_reason = " | ".join(exit_reason_parts) if exit_signal else ""

    # -- Position sizing (when entering) -------------------
    suggested_shares: Optional[int] = None
    suggested_cost: Optional[float] = None

    if entry_signal and atr20 is not None and atr20 > 0:
        risk_dollars = current_equity * risk_per_trade
        stop_distance = atr_multiplier * atr20
        risk_shares = math.floor(risk_dollars / stop_distance)
        capital_shares = math.floor(current_equity * max_position_pct / close)
        shares = min(risk_shares, capital_shares)
        if shares > 0:
            suggested_shares = shares
            suggested_cost = shares * close

    return SymbolSignal(
        symbol=symbol,
        signal_date=signal_date,
        close=close,
        entry_high=entry_high,
        exit_low=exit_low,
        sma200=sma200,
        atr20=atr20,
        entry_signal=entry_signal,
        exit_signal=exit_signal,
        suggested_shares=suggested_shares,
        suggested_cost=suggested_cost,
        entry_reason=entry_reason,
        exit_reason=exit_reason,
    )


def generate_all_signals(
    market_data: Dict[str, pd.DataFrame],
    current_equity: float,
    held_symbols: List[str],
    open_position_count: int,
    **override_params,
) -> List[SymbolSignal]:
    """
    Generate signals for all symbols in *market_data*.
    Returns a list sorted by entry priority (most extended breakout first).
    """
    signals: List[SymbolSignal] = []
    held_set = set(s.upper() for s in held_symbols)

    for symbol, df in market_data.items():
        sig = generate_signal(
            symbol=symbol,
            df=df,
            current_equity=current_equity,
            already_held=symbol.upper() in held_set,
            open_position_count=open_position_count,
            **override_params,
        )
        if sig is not None:
            signals.append(sig)

    signals.sort(
        key=lambda s: (
            s.close / s.sma200 if (s.entry_signal and s.sma200 and s.sma200 > 0) else 0
        ),
        reverse=True,
    )
    return signals
