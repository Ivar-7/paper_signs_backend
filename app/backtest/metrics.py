"""
Performance metrics                    all pure functions, no I/O.

Accepts an equity curve list and trade list.
Returns a dict suitable for unpacking into BacktestResult.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


def compute_metrics(
    equity_curve: List[Dict],  # [{date: str, equity: float}, ...]
    trades: list,              # List[BacktestTrade]
    initial_equity: float,
) -> Dict:
    """
    Compute all performance metrics from an equity curve and trade list.
    Returns a dict ready to unpack into BacktestResult fields.
    """
    if not equity_curve:
        return _empty_metrics()

    equities = [e["equity"] for e in equity_curve]
    dates = pd.to_datetime([e["date"] for e in equity_curve])

    final_equity = equities[-1]
    years = max((dates[-1] - dates[0]).days / 365.25, 1 / 365.25)

    # CAGR
    cagr = (final_equity / initial_equity) ** (1 / years) - 1 if initial_equity > 0 else 0.0

    # Daily returns
    equity_series = pd.Series(equities, index=dates)
    daily_returns = equity_series.pct_change().dropna()

    # Sharpe (annualised, risk-free = 0)
    if daily_returns.std() > 0:
        sharpe = (daily_returns.mean() / daily_returns.std()) * math.sqrt(252)
    else:
        sharpe = 0.0

    # Sortino (downside deviation only)
    downside = daily_returns[daily_returns < 0]
    if len(downside) > 0 and downside.std() > 0:
        sortino = (daily_returns.mean() / downside.std()) * math.sqrt(252)
    else:
        sortino = 0.0 if len(downside) == 0 else float("inf")

    # Max drawdown
    running_max = equity_series.cummax()
    drawdowns = (equity_series - running_max) / running_max
    max_drawdown = float(drawdowns.min())

    # Trade-level metrics
    pnls = [t.pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total_trades = len(pnls)
    win_rate = len(wins) / total_trades if total_trades > 0 else 0.0
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

    avg_holding_days = (
        float(np.mean([t.holding_days for t in trades]))
        if trades else 0.0
    )

    return {
        "cagr": round(cagr, 4),
        "max_drawdown": round(max_drawdown, 4),
        "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3),
        "profit_factor": round(profit_factor, 3),
        "win_rate": round(win_rate, 4),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "total_trades": total_trades,
        "avg_holding_days": round(avg_holding_days, 1),
        "final_equity": round(final_equity, 2),
    }


def _empty_metrics() -> Dict:
    return {
        "cagr": 0.0,
        "max_drawdown": 0.0,
        "sharpe": 0.0,
        "sortino": 0.0,
        "profit_factor": 0.0,
        "win_rate": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "total_trades": 0,
        "avg_holding_days": 0.0,
        "final_equity": 0.0,
    }


def calmar_ratio(cagr: float, max_drawdown: float) -> float:
    """CAGR / abs(MaxDrawdown). Returns 0 if max_drawdown is zero."""
    dd = abs(max_drawdown)
    return cagr / dd if dd > 0 else 0.0


def monte_carlo_drawdown(
    trades_pnl: List[float],
    initial_equity: float,
    simulations: int = 1000,
    seed: int = 42,
) -> Dict:
    """
    Monte Carlo shuffle trades to estimate drawdown distribution.
    Returns {p50, p95, p99} worst drawdowns across simulations.
    """
    if not trades_pnl:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

    rng = np.random.default_rng(seed)
    arr = np.array(trades_pnl)
    worst_drawdowns = []

    for _ in range(simulations):
        shuffled = rng.permutation(arr)
        equity = initial_equity + np.cumsum(shuffled)
        equity = np.concatenate([[initial_equity], equity])
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max
        worst_drawdowns.append(float(drawdown.min()))

    worst = np.array(worst_drawdowns)
    return {
        "p50": round(float(np.percentile(worst, 50)), 4),
        "p95": round(float(np.percentile(worst, 95)), 4),
        "p99": round(float(np.percentile(worst, 99)), 4),
    }
