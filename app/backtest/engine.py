"""
Vectorized backtest engine.

Signal generated at close[t]    '                                      order fills at open[t+1].
No look-ahead bias. Includes transaction cost modeling.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from paper_signs_backend.app.data.market import get_all_symbols
from paper_signs_backend.app.strategy.indicators import add_all_indicators
from paper_signs_backend.app.config import get_settings
from paper_signs_backend.app.strategy.constants import (
    ATR_LENGTH, ATR_MULTIPLIER, BACKTEST_PERIODS,
    ENTRY_LOOKBACK, EXIT_LOOKBACK, INITIAL_CAPITAL,
    MAX_POSITION_PCT, MAX_POSITIONS, RISK_PER_TRADE, SMA_LENGTH,
)

_settings = get_settings()

logger = logging.getLogger(__name__)


#    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
# Data classes
#    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  

@dataclass
class BacktestTrade:
    symbol: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    shares: int
    pnl: float
    pnl_pct: float
    holding_days: int


@dataclass
class BacktestResult:
    period_name: str
    start_date: str
    end_date: str
    initial_equity: float
    final_equity: float
    equity_curve: List[Dict]        # [{date, equity}, ...]
    trades: List[BacktestTrade]
    per_symbol: Dict[str, Dict]     # symbol    '                                      {trades, pnl, win_rate}
    parameters: Dict                # snapshot of params used
    cagr: float = 0.0
    max_drawdown: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    profit_factor: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    total_trades: int = 0
    avg_holding_days: float = 0.0


#    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
# Core engine
#    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  

class BacktestEngine:
    """
    Event-driven daily backtest engine.

    Rules:
    - Entry signal fires at close[t]; order fills at open[t+1]
    - Exit signal fires at close[t]; order fills at open[t+1]
    - Position sizing: ATR(20) risk sizing, capped at max_position_pct
    - Max simultaneous positions enforced
    - Transaction costs applied on both legs
    """

    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        initial_capital: Optional[float] = None,
        risk_per_trade: Optional[float] = None,
        max_positions: Optional[int] = None,
        max_position_pct: Optional[float] = None,
        entry_lookback: Optional[int] = None,
        exit_lookback: Optional[int] = None,
        sma_length: Optional[int] = None,
        atr_length: Optional[int] = None,
        atr_multiplier: Optional[float] = None,
        commission_pct: float = 0.001,  # 0.10% per side
    ) -> None:
        self.symbols = symbols or list(BACKTEST_PERIODS.keys())
        self.initial_capital = initial_capital or INITIAL_CAPITAL
        self.risk_per_trade = risk_per_trade or RISK_PER_TRADE
        self.max_positions = max_positions or MAX_POSITIONS
        self.max_position_pct = max_position_pct or MAX_POSITION_PCT
        self.entry_lookback = entry_lookback or ENTRY_LOOKBACK
        self.exit_lookback = exit_lookback or EXIT_LOOKBACK
        self.sma_length = sma_length or SMA_LENGTH
        self.atr_length = atr_length or ATR_LENGTH
        self.atr_multiplier = atr_multiplier or ATR_MULTIPLIER
        self.commission_pct = commission_pct

    def _prepare_data(
        self,
        start: Optional[str],
        end: Optional[str],
        market_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Load and compute indicators for all symbols."""
        # Fetch with a warm-up buffer to ensure indicators are valid at start date
        warmup_start = None
        if start:
            warmup_start = pd.Timestamp(start) - pd.DateOffset(days=self.sma_length * 2)
            warmup_start = warmup_start.strftime("%Y-%m-%d")

        raw = market_data or get_all_symbols(
            symbols=self.symbols,
            start=warmup_start,
            end=end,
        )

        prepared: Dict[str, pd.DataFrame] = {}
        for sym, df in raw.items():
            df = add_all_indicators(
                df,
                sma_length=self.sma_length,
                entry_lookback=self.entry_lookback,
                exit_lookback=self.exit_lookback,
                atr_length=self.atr_length,
            )
            # Shift signals: signal at close[t]    '                                      next open[t+1]
            df["FillOpen"] = df["Open"].shift(-1)
            prepared[sym] = df

        return prepared

    def run(
        self,
        period_name: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        market_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> BacktestResult:
        """Execute the full backtest for a given period."""
        logger.info("Backtest [%s] start=%s end=%s", period_name, start, end)

        prepared = self._prepare_data(start=start, end=end, market_data=market_data)
        if not prepared:
            raise RuntimeError("No market data available for backtest")

        # Determine common date index within the test window
        all_dates = sorted(
            set.intersection(*[set(df.index) for df in prepared.values()])
        )
        if start:
            all_dates = [d for d in all_dates if d >= pd.Timestamp(start)]
        if end:
            all_dates = [d for d in all_dates if d <= pd.Timestamp(end)]

        if not all_dates:
            raise RuntimeError(f"No common dates in range [{start}, {end}]")

        #    '                                     '                                   State    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
        cash = self.initial_capital
        # symbol    '                                      {shares, entry_price, entry_date, atr_at_entry}
        positions: Dict[str, Dict] = {}
        equity_curve: List[Dict] = []
        all_trades: List[BacktestTrade] = []

        sma_col = f"SMA{self.sma_length}"
        atr_col = f"ATR{self.atr_length}"

        for dt in all_dates:
            #    '                                     '                                   Mark-to-market equity    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
            market_value = sum(
                pos["shares"] * float(prepared[sym].loc[dt, "Close"])
                for sym, pos in positions.items()
                if sym in prepared and dt in prepared[sym].index
            )
            equity = cash + market_value
            equity_curve.append({"date": dt.strftime("%Y-%m-%d"), "equity": round(equity, 2)})

            #    '                                     '                                   1. Process exits    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
            for sym in list(positions.keys()):
                if sym not in prepared or dt not in prepared[sym].index:
                    continue
                row = prepared[sym].loc[dt]
                close = float(row["Close"])
                exit_low = row.get("ExitLow")
                sma = row.get(sma_col)

                exit_triggered = False
                if not pd.isna(exit_low) and close < float(exit_low):
                    exit_triggered = True
                if not pd.isna(sma) and close < float(sma):
                    exit_triggered = True

                if exit_triggered:
                    fill_open = row.get("FillOpen")
                    fill_price = float(fill_open) if (fill_open is not None and not pd.isna(fill_open)) else close
                    pos = positions[sym]
                    shares = pos["shares"]
                    proceeds = shares * fill_price * (1 - self.commission_pct)
                    pnl = proceeds - pos["cost"]
                    pnl_pct = pnl / pos["cost"] if pos["cost"] > 0 else 0.0
                    holding_days = (dt - pd.Timestamp(pos["entry_date"])).days

                    cash += proceeds
                    all_trades.append(BacktestTrade(
                        symbol=sym,
                        entry_date=pos["entry_date"],
                        exit_date=dt.strftime("%Y-%m-%d"),
                        entry_price=pos["entry_price"],
                        exit_price=fill_price,
                        shares=shares,
                        pnl=round(pnl, 2),
                        pnl_pct=round(pnl_pct * 100, 2),
                        holding_days=holding_days,
                    ))
                    del positions[sym]

            #    '                                     '                                   2. Process entries    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
            if len(positions) < self.max_positions:
                candidates = []
                for sym, df in prepared.items():
                    if sym in positions or dt not in df.index:
                        continue
                    row = df.loc[dt]
                    close = float(row["Close"])
                    entry_high = row.get("EntryHigh")
                    sma = row.get(sma_col)
                    atr = row.get(atr_col)

                    if any(pd.isna(v) for v in [entry_high, sma, atr]):
                        continue

                    if close > float(entry_high) and close > float(sma):
                        candidates.append({
                            "symbol": sym,
                            "close": close,
                            "sma": float(sma),
                            "atr": float(atr),
                            "row": row,
                            "strength": close / float(sma),
                        })

                # Prioritise strongest trend
                candidates.sort(key=lambda x: x["strength"], reverse=True)

                for cand in candidates:
                    if len(positions) >= self.max_positions:
                        break

                    sym = cand["symbol"]
                    close = cand["close"]
                    atr = cand["atr"]
                    fill_open = cand["row"].get("FillOpen")
                    fill_price = float(fill_open) if (fill_open is not None and not pd.isna(fill_open)) else close

                    risk_dollars = equity * self.risk_per_trade
                    stop_distance = self.atr_multiplier * atr
                    if stop_distance <= 0:
                        continue
                    risk_shares = math.floor(risk_dollars / stop_distance)
                    capital_shares = math.floor(equity * self.max_position_pct / fill_price)
                    shares = min(risk_shares, capital_shares)

                    cost = shares * fill_price * (1 + self.commission_pct)
                    if shares <= 0 or cost > cash:
                        continue

                    cash -= cost
                    positions[sym] = {
                        "shares": shares,
                        "entry_price": round(fill_price, 4),
                        "entry_date": dt.strftime("%Y-%m-%d"),
                        "cost": cost,
                    }

        #    '                                     '                                   Final mark-to-market for open positions    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
        last_dt = all_dates[-1]
        for sym, pos in positions.items():
            if sym in prepared and last_dt in prepared[sym].index:
                last_price = float(prepared[sym].loc[last_dt, "Close"])
                proceeds = pos["shares"] * last_price * (1 - self.commission_pct)
                pnl = proceeds - pos["cost"]
                pnl_pct = pnl / pos["cost"] if pos["cost"] > 0 else 0.0
                all_trades.append(BacktestTrade(
                    symbol=sym,
                    entry_date=pos["entry_date"],
                    exit_date=last_dt.strftime("%Y-%m-%d"),
                    entry_price=pos["entry_price"],
                    exit_price=last_price,
                    shares=pos["shares"],
                    pnl=round(pnl, 2),
                    pnl_pct=round(pnl_pct * 100, 2),
                    holding_days=(last_dt - pd.Timestamp(pos["entry_date"])).days,
                ))

        #    '                                     '                                   Compute metrics    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
        from paper_signs_backend.app.backtest.metrics import compute_metrics
        metrics = compute_metrics(
            equity_curve=equity_curve,
            trades=all_trades,
            initial_equity=self.initial_capital,
        )

        #    '                                     '                                   Per-symbol breakdown    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
        per_symbol: Dict[str, Dict] = {}
        for trade in all_trades:
            s = trade.symbol
            if s not in per_symbol:
                per_symbol[s] = {"trades": 0, "pnl": 0.0, "wins": 0, "losses": 0}
            per_symbol[s]["trades"] += 1
            per_symbol[s]["pnl"] += trade.pnl
            if trade.pnl >= 0:
                per_symbol[s]["wins"] += 1
            else:
                per_symbol[s]["losses"] += 1
        for s, d in per_symbol.items():
            d["win_rate"] = round(d["wins"] / d["trades"] * 100, 1) if d["trades"] > 0 else 0.0

        result = BacktestResult(
            period_name=period_name,
            start_date=all_dates[0].strftime("%Y-%m-%d"),
            end_date=all_dates[-1].strftime("%Y-%m-%d"),
            initial_equity=self.initial_capital,
            equity_curve=equity_curve,
            trades=all_trades,
            per_symbol=per_symbol,
            parameters=self._params_snapshot(),
            **metrics,
        )

        logger.info(
            "Backtest [%s] complete: %d trades, CAGR=%.1f%%, MaxDD=%.1f%%",
            period_name,
            result.total_trades,
            result.cagr * 100,
            result.max_drawdown * 100,
        )
        return result

    def _params_snapshot(self) -> Dict:
        return {
            "initial_capital": self.initial_capital,
            "risk_per_trade": self.risk_per_trade,
            "max_positions": self.max_positions,
            "max_position_pct": self.max_position_pct,
            "entry_lookback": self.entry_lookback,
            "exit_lookback": self.exit_lookback,
            "sma_length": self.sma_length,
            "atr_length": self.atr_length,
            "atr_multiplier": self.atr_multiplier,
            "commission_pct": self.commission_pct,
            "symbols": self.symbols,
        }


#    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
# Robustness test helpers
#    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  

def run_parameter_perturbation(
    period_name: str = "validation",
    market_data: Optional[Dict[str, pd.DataFrame]] = None,
) -> List[Dict]:
    """
    Run the backtest across a grid of parameter variations.
    Returns a list of result dicts.
    """
    date_range = BACKTEST_PERIODS.get(period_name, ("2020-01-01", "2023-12-31"))
    start, end = date_range

    entry_variants = [80, 90, 100, 110, 120]
    exit_variants = [40, 50, 60, 70]
    sma_variants = [150, 175, 200, 225, 250]

    results = []
    for entry in entry_variants:
        for sma in sma_variants:
            engine = BacktestEngine(entry_lookback=entry, sma_length=sma)
            try:
                r = engine.run(
                    period_name=period_name,
                    start=start,
                    end=end,
                    market_data=market_data,
                )
                results.append({
                    "test_type": "perturbation",
                    "test_label": f"entry={entry} sma={sma}",
                    "entry_lookback": entry,
                    "sma_length": sma,
                    "cagr": r.cagr,
                    "max_drawdown": r.max_drawdown,
                    "sharpe": r.sharpe,
                    "profit_factor": r.profit_factor,
                    "total_trades": r.total_trades,
                })
            except Exception as exc:
                logger.error("Perturbation failed entry=%d sma=%d: %s", entry, sma, exc)

    return results


def run_market_removal(
    period_name: str = "validation",
    market_data: Optional[Dict[str, pd.DataFrame]] = None,
) -> List[Dict]:
    """Remove one market at a time and re-run the backtest."""
    date_range = BACKTEST_PERIODS.get(period_name, ("2020-01-01", "2023-12-31"))
    start, end = date_range

    results = []
    all_syms = list(BACKTEST_PERIODS.keys())

    for removed_sym in all_syms:
        remaining = [s for s in all_syms if s != removed_sym]
        engine = BacktestEngine(symbols=remaining)
        try:
            r = engine.run(
                period_name=period_name,
                start=start,
                end=end,
                market_data={k: v for k, v in (market_data or {}).items() if k != removed_sym},
            )
            results.append({
                "test_type": "market_removal",
                "test_label": f"removed={removed_sym}",
                "removed_symbol": removed_sym,
                "cagr": r.cagr,
                "max_drawdown": r.max_drawdown,
                "sharpe": r.sharpe,
                "profit_factor": r.profit_factor,
                "total_trades": r.total_trades,
            })
        except Exception as exc:
            logger.error("Market removal test failed for %s: %s", removed_sym, exc)

    return results


def run_cost_stress(
    period_name: str = "validation",
    market_data: Optional[Dict[str, pd.DataFrame]] = None,
) -> List[Dict]:
    """Run with increasing transaction costs."""
    date_range = BACKTEST_PERIODS.get(period_name, ("2020-01-01", "2023-12-31"))
    start, end = date_range

    costs = [0.0, 0.0005, 0.001, 0.002]
    results = []
    for cost in costs:
        engine = BacktestEngine(commission_pct=cost)
        try:
            r = engine.run(
                period_name=period_name,
                start=start,
                end=end,
                market_data=market_data,
            )
            results.append({
                "test_type": "cost_stress",
                "test_label": f"commission={cost*100:.2f}%",
                "commission_pct": cost,
                "cagr": r.cagr,
                "max_drawdown": r.max_drawdown,
                "sharpe": r.sharpe,
                "profit_factor": r.profit_factor,
                "total_trades": r.total_trades,
            })
        except Exception as exc:
            logger.error("Cost stress test failed at %s: %s", cost, exc)

    return results
