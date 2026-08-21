"""
Strategy scoring and probability engine.

Evaluates market setups against the Donchian 100/50 + SMA200 + ATR20 trend following rules
to derive objective success probability scores (0-100%), recommendation badges,
stop loss (SL) levels, take profit (TP) targets, and risk:reward ratios.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from paper_signs_backend.app.strategy.constants import (
    ATR_LENGTH,
    ATR_MULTIPLIER,
    ENTRY_LOOKBACK,
    EXIT_LOOKBACK,
    SMA_LENGTH,
)


@dataclass
class StrategyChecklist:
    trend_above_sma200: bool
    breakout_donchian_high: bool
    volatility_healthy: bool
    volume_confirmed: bool
    details: Dict[str, str] = field(default_factory=dict)


@dataclass
class ScoringResult:
    score: float                      # 0 to 100%
    recommendation: str               # STRONG BUY, BUY, WATCHLIST, NEUTRAL, EXIT, AVOID
    stop_loss: Optional[float]
    stop_loss_pct: Optional[float]
    take_profit_1: Optional[float]    # 1.5R target
    take_profit_2: Optional[float]    # 2.5R target
    take_profit_3: Optional[float]    # 4.0R target
    risk_reward_ratio: Optional[float]
    distance_to_breakout_pct: float   # % from current price to EntryHigh (>0 means above, <0 means below)
    sma200_clearance_pct: float       # % distance above/below SMA200
    checklist: StrategyChecklist


def calculate_strategy_score(
    df: pd.DataFrame,
    symbol: str,
    already_held: bool = False,
    entry_lookback: int = ENTRY_LOOKBACK,
    exit_lookback: int = EXIT_LOOKBACK,
    sma_length: int = SMA_LENGTH,
    atr_length: int = ATR_LENGTH,
    atr_multiplier: float = ATR_MULTIPLIER,
) -> Optional[ScoringResult]:
    """
    Calculate an objective probability score and price targets for a symbol.
    
    Scoring Breakdown (100 pts max):
      1. Donchian Breakout Clearance (35 pts):
         - Current Close >= 100d High: 30 pts (Active Breakout) + up to 5 pts for clearance
         - If within 1.5% of breakout: 20 pts
         - If within 3.0% of breakout: 10 pts
      2. SMA200 Trend Strength & Alignment (30 pts):
         - Current Close > SMA200: 20 pts
         - SMA200 upward slope (20d): 10 pts
      3. Volatility Structure & ATR Quality (20 pts):
         - ATR20 / Close between 1.0% and 4.0% (healthy trend expansion): 15 pts
         - ATR20 compression or non-extreme volatility: 5 pts
      4. Volume Confirmation (15 pts):
         - Current Volume > 20-day Volume SMA: 15 pts (or 8 pts if neutral/missing)
    """
    if len(df) < max(sma_length, entry_lookback) + 10:
        return None

    row = df.iloc[-1]
    close = float(row["Close"]) if "Close" in row and not np.isnan(row["Close"]) else None
    if close is None or close <= 0:
        return None

    entry_high = float(row.get("EntryHigh", np.nan))
    exit_low = float(row.get("ExitLow", np.nan))
    sma200 = float(row.get(f"SMA{sma_length}", np.nan))
    atr20 = float(row.get(f"ATR{atr_length}", np.nan))

    if np.isnan(entry_high) or np.isnan(exit_low) or np.isnan(sma200):
        return None

    has_atr = not np.isnan(atr20) and atr20 > 0
    atr_val = atr20 if has_atr else (close * 0.02)

    # 1. Breakout Clearance Metric
    distance_to_breakout_pct = ((close - entry_high) / entry_high) * 100.0
    breakout_score = 0.0
    if close >= entry_high:
        breakout_score = 30.0 + min(5.0, max(0.0, distance_to_breakout_pct * 1.5))
    elif distance_to_breakout_pct >= -1.5:
        breakout_score = 22.0
    elif distance_to_breakout_pct >= -3.5:
        breakout_score = 14.0
    elif distance_to_breakout_pct >= -7.0:
        breakout_score = 6.0
    else:
        breakout_score = 0.0

    # 2. SMA200 Trend Strength Metric
    sma200_clearance_pct = ((close - sma200) / sma200) * 100.0
    trend_score = 0.0
    sma200_slope_positive = False

    if f"SMA{sma_length}" in df.columns and len(df) >= 25:
        prev_sma = df[f"SMA{sma_length}"].iloc[-20]
        if not np.isnan(prev_sma) and prev_sma > 0:
            sma200_slope_positive = sma200 > prev_sma

    if close > sma200:
        trend_score += 20.0
        if sma200_slope_positive:
            trend_score += 10.0
        elif sma200_clearance_pct > 2.0:
            trend_score += 5.0
    else:
        trend_score = 0.0

    # 3. Volatility Metric (ATR % of price)
    volatility_score = 0.0
    atr_pct = (atr_val / close) * 100.0
    if 0.8 <= atr_pct <= 3.8:
        volatility_score = 20.0
    elif 0.5 <= atr_pct <= 5.5:
        volatility_score = 14.0
    else:
        volatility_score = 8.0

    # 4. Volume Confirmation Metric
    volume_score = 10.0  # default neutral
    volume_confirmed = False
    if "Volume" in df.columns and len(df) >= 25:
        vol_series = df["Volume"].dropna()
        if len(vol_series) >= 20:
            vol_sma20 = vol_series.rolling(20).mean().iloc[-1]
            cur_vol = vol_series.iloc[-1]
            if not np.isnan(vol_sma20) and vol_sma20 > 0 and cur_vol > vol_sma20:
                volume_score = 15.0
                volume_confirmed = True
            else:
                volume_score = 8.0

    total_score = min(100.0, max(0.0, breakout_score + trend_score + volatility_score + volume_score))

    # Stop Loss & Target calculations
    stop_distance = atr_multiplier * atr_val
    stop_loss = round(max(0.01, close - stop_distance), 2)
    stop_loss_pct = round(((stop_loss - close) / close) * 100.0, 2)

    take_profit_1 = round(close + (1.5 * stop_distance), 2)
    take_profit_2 = round(close + (2.5 * stop_distance), 2)
    take_profit_3 = round(close + (4.0 * stop_distance), 2)

    risk_reward_ratio = round((take_profit_2 - close) / max(0.01, close - stop_loss), 2)

    # Determine Recommendation
    is_exit = already_held and (close < exit_low or close < sma200)
    is_breakout = close >= entry_high and close > sma200

    if is_exit:
        recommendation = "EXIT"
        total_score = min(total_score, 25.0)
    elif is_breakout:
        if total_score >= 80.0:
            recommendation = "STRONG BUY"
        else:
            recommendation = "BUY"
    elif close > sma200 and distance_to_breakout_pct >= -3.0:
        recommendation = "WATCHLIST"
    elif close > sma200:
        recommendation = "NEUTRAL"
    else:
        recommendation = "AVOID"
        total_score = min(total_score, 35.0)

    checklist = StrategyChecklist(
        trend_above_sma200=close > sma200,
        breakout_donchian_high=close >= entry_high,
        volatility_healthy=volatility_score >= 14.0,
        volume_confirmed=volume_confirmed,
        details={
            "sma200": f"Price ${close:.2f} vs SMA200 ${sma200:.2f} ({sma200_clearance_pct:+.1f}%)",
            "donchian": f"Price ${close:.2f} vs 100d High ${entry_high:.2f} ({distance_to_breakout_pct:+.1f}%)",
            "atr": f"ATR20 ${atr_val:.2f} ({atr_pct:.1f}% of price)",
            "stop_loss": f"${stop_loss:.2f} ({stop_loss_pct:.1f}%)",
            "tp1": f"${take_profit_1:.2f} (1.5R)",
            "tp2": f"${take_profit_2:.2f} (2.5R)",
        },
    )

    return ScoringResult(
        score=round(total_score, 1),
        recommendation=recommendation,
        stop_loss=stop_loss,
        stop_loss_pct=stop_loss_pct,
        take_profit_1=take_profit_1,
        take_profit_2=take_profit_2,
        take_profit_3=take_profit_3,
        risk_reward_ratio=risk_reward_ratio,
        distance_to_breakout_pct=round(distance_to_breakout_pct, 2),
        sma200_clearance_pct=round(sma200_clearance_pct, 2),
        checklist=checklist,
    )
