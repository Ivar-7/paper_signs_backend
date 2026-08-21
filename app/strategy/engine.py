"""
Strategizer engine facade.

Provides unified market scanning, ranking, and symbol deep-dive analysis.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np

from paper_signs_backend.app.broker import get_broker
from paper_signs_backend.app.config import get_settings
from paper_signs_backend.app.data.market import get_all_symbols, get_ohlcv
from paper_signs_backend.app.strategy.constants import (
    ATR_LENGTH,
    ENTRY_LOOKBACK,
    EXIT_LOOKBACK,
    SMA_LENGTH,
)
from paper_signs_backend.app.strategy.indicators import add_all_indicators
from paper_signs_backend.app.strategy.signals import SymbolSignal, generate_all_signals, generate_signal

settings = get_settings()


def scan_all_markets(
    symbols: Optional[List[str]] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Perform a complete strategy scan across tracked symbols.
    Returns ranked opportunities, market summary stats, sparklines, and account context.
    """
    broker = get_broker()
    account = broker.get_account()
    held_symbols = [p.symbol for p in account.positions]
    open_count = len(held_symbols)

    target_symbols = symbols or settings.symbol_list
    market_data = get_all_symbols(symbols=target_symbols, force_refresh=force_refresh)

    signals = generate_all_signals(
        market_data=market_data,
        current_equity=account.equity,
        held_symbols=held_symbols,
        open_position_count=open_count,
    )

    strong_buys = sum(1 for s in signals if s.recommendation == "STRONG BUY")
    buys = sum(1 for s in signals if s.recommendation == "BUY")
    watchlists = sum(1 for s in signals if s.recommendation == "WATCHLIST")
    exits = sum(1 for s in signals if s.recommendation == "EXIT")

    best_opportunity = signals[0] if signals else None

    market_items = []
    for s in signals:
        df = market_data.get(s.symbol)
        change_24h = 0.0
        sparkline = []
        if df is not None and len(df) >= 2:
            closes = df["Close"].dropna()
            if len(closes) >= 2:
                prev_c = float(closes.iloc[-2])
                cur_c = float(closes.iloc[-1])
                if prev_c > 0:
                    change_24h = round(((cur_c - prev_c) / prev_c) * 100.0, 2)
            sparkline = [round(float(c), 2) for c in closes.tail(14).tolist()]

        market_items.append({
            "symbol": s.symbol,
            "signal_date": s.signal_date,
            "close": s.close,
            "change_24h_pct": change_24h,
            "sparkline": sparkline,
            "entry_high": s.entry_high,
            "exit_low": s.exit_low,
            "sma200": s.sma200,
            "atr20": s.atr20,
            "probability_score": s.probability_score,
            "recommendation": s.recommendation,
            "entry_signal": s.entry_signal,
            "exit_signal": s.exit_signal,
            "stop_loss": s.stop_loss,
            "stop_loss_pct": s.stop_loss_pct,
            "take_profit_1": s.take_profit_1,
            "take_profit_2": s.take_profit_2,
            "take_profit_3": s.take_profit_3,
            "risk_reward_ratio": s.risk_reward_ratio,
            "distance_to_breakout_pct": s.distance_to_breakout_pct,
            "sma200_clearance_pct": s.sma200_clearance_pct,
            "suggested_shares": s.suggested_shares,
            "suggested_cost": s.suggested_cost,
            "entry_reason": s.entry_reason,
            "exit_reason": s.exit_reason,
            "is_held": s.symbol.upper() in [h.upper() for h in held_symbols],
            "checklist": s.checklist,
        })

    return {
        "account": {
            "equity": round(account.equity, 2),
            "cash": round(account.cash, 2),
            "open_positions": open_count,
            "max_positions": 4,
        },
        "stats": {
            "total_scanned": len(signals),
            "strong_buys": strong_buys,
            "buys": buys,
            "watchlists": watchlists,
            "exits": exits,
            "best_opportunity_symbol": best_opportunity.symbol if best_opportunity else None,
            "best_opportunity_score": best_opportunity.probability_score if best_opportunity else 0.0,
        },
        "markets": market_items,
    }


def get_symbol_analysis(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Get in-depth strategy analysis and historical candle data with indicators for a symbol.
    """
    broker = get_broker()
    account = broker.get_account()
    held_symbols = [p.symbol for p in account.positions]

    try:
        df = get_ohlcv(symbol, period="2y")
        if df.empty or len(df) < 110:
            return None
    except Exception:
        return None

    sig = generate_signal(
        symbol=symbol,
        df=df,
        current_equity=account.equity,
        already_held=symbol.upper() in [h.upper() for h in held_symbols],
        open_position_count=len(held_symbols),
    )
    if not sig:
        return None

    df_ind = add_all_indicators(df)
    recent = df_ind.tail(60)
    history_points = []
    for idx, r in recent.iterrows():
        history_points.append({
            "date": str(idx.date()),
            "open": round(float(r["Open"]), 2) if "Open" in r else None,
            "high": round(float(r["High"]), 2) if "High" in r else None,
            "low": round(float(r["Low"]), 2) if "Low" in r else None,
            "close": round(float(r["Close"]), 2),
            "volume": int(r["Volume"]) if "Volume" in r and not pd.isna(r["Volume"]) else 0,
            "entry_high": round(float(r["EntryHigh"]), 2) if not pd.isna(r.get("EntryHigh")) else None,
            "exit_low": round(float(r["ExitLow"]), 2) if not pd.isna(r.get("ExitLow")) else None,
            "sma200": round(float(r[f"SMA{SMA_LENGTH}"]), 2) if not pd.isna(r.get(f"SMA{SMA_LENGTH}")) else None,
        })

    return {
        "symbol": sig.symbol,
        "signal_date": sig.signal_date,
        "close": sig.close,
        "entry_high": sig.entry_high,
        "exit_low": sig.exit_low,
        "sma200": sig.sma200,
        "atr20": sig.atr20,
        "probability_score": sig.probability_score,
        "recommendation": sig.recommendation,
        "entry_signal": sig.entry_signal,
        "exit_signal": sig.exit_signal,
        "stop_loss": sig.stop_loss,
        "stop_loss_pct": sig.stop_loss_pct,
        "take_profit_1": sig.take_profit_1,
        "take_profit_2": sig.take_profit_2,
        "take_profit_3": sig.take_profit_3,
        "risk_reward_ratio": sig.risk_reward_ratio,
        "distance_to_breakout_pct": sig.distance_to_breakout_pct,
        "sma200_clearance_pct": sig.sma200_clearance_pct,
        "suggested_shares": sig.suggested_shares,
        "suggested_cost": sig.suggested_cost,
        "is_held": sig.symbol.upper() in [h.upper() for h in held_symbols],
        "checklist": sig.checklist,
        "history": history_points,
    }
