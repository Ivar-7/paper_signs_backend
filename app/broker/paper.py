"""
Internal paper trading simulation broker.

No external API required. State is persisted via the database layer.
This broker simulates market-order fills using the last available price
from yfinance (approximating the next open when running after market close).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from paper_signs_backend.app.broker.base import BaseBroker, BrokerAccount, BrokerPosition, OrderResult
from paper_signs_backend.app.config import get_settings
from paper_signs_backend.app.data.market import get_ohlcv
from paper_signs_backend.app.strategy.constants import INITIAL_CAPITAL

logger = logging.getLogger(__name__)
settings = get_settings()

# State file path (alongside the database)
_STATE_FILE = "paper_state.json"


def _load_state() -> Dict[str, Any]:
    if os.path.exists(_STATE_FILE):
        with open(_STATE_FILE, "r") as f:
            return json.load(f)
    return {
        "cash": INITIAL_CAPITAL,
        "positions": {},  # symbol -> {shares, avg_entry_price, entry_date}
    }


def _save_state(state: Dict[str, Any]) -> None:
    with open(_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


class PaperBroker(BaseBroker):
    """Zero-cost paper trading simulator backed by a JSON state file."""

    def __init__(self) -> None:
        self._state = _load_state()

    def _persist(self) -> None:
        _save_state(self._state)

    def get_last_price(self, symbol: str) -> Optional[float]:
        try:
            df = get_ohlcv(symbol, period="5d")
            return float(df["Close"].iloc[-1])
        except Exception as exc:
            logger.error("PaperBroker: failed to fetch price for %s: %s", symbol, exc)
            return None

    def get_account(self) -> BrokerAccount:
        positions: List[BrokerPosition] = []
        total_market_value = 0.0

        for symbol, pos in self._state["positions"].items():
            price = self.get_last_price(symbol)
            mkt_val = (price or pos["avg_entry_price"]) * pos["shares"]
            total_market_value += mkt_val
            unrealized = (
                ((price - pos["avg_entry_price"]) * pos["shares"])
                if price is not None
                else None
            )
            positions.append(
                BrokerPosition(
                    symbol=symbol,
                    shares=pos["shares"],
                    avg_entry_price=pos["avg_entry_price"],
                    current_price=price,
                    unrealized_pnl=unrealized,
                    entry_date=pos.get("entry_date"),
                )
            )

        equity = self._state["cash"] + total_market_value
        return BrokerAccount(
            equity=equity,
            cash=self._state["cash"],
            positions=positions,
        )

    def submit_buy(
        self,
        symbol: str,
        shares: int,
        note: Optional[str] = None,
    ) -> OrderResult:
        price = self.get_last_price(symbol)
        if price is None:
            return OrderResult(
                symbol=symbol,
                action="BUY",
                shares=shares,
                filled_price=0.0,
                success=False,
                error="Could not fetch price",
            )

        cost = shares * price
        if cost > self._state["cash"]:
            # Re-size to available cash
            shares = int(self._state["cash"] // price)
            cost = shares * price
            if shares <= 0:
                return OrderResult(
                    symbol=symbol,
                    action="BUY",
                    shares=0,
                    filled_price=price,
                    success=False,
                    error="Insufficient cash",
                )

        self._state["cash"] -= cost

        existing = self._state["positions"].get(symbol)
        if existing:
            # Average in (shouldn't normally happen, but handle it gracefully)
            total_shares = existing["shares"] + shares
            avg_price = (
                (existing["shares"] * existing["avg_entry_price"] + shares * price)
                / total_shares
            )
            self._state["positions"][symbol] = {
                "shares": total_shares,
                "avg_entry_price": round(avg_price, 4),
                "entry_date": existing["entry_date"],
            }
        else:
            self._state["positions"][symbol] = {
                "shares": shares,
                "avg_entry_price": round(price, 4),
                "entry_date": date.today().isoformat(),
            }

        self._persist()
        logger.info("PaperBroker BUY %s    '         %d @ %.4f", symbol, shares, price)
        return OrderResult(
            symbol=symbol,
            action="BUY",
            shares=shares,
            filled_price=price,
            cost=cost,
            success=True,
        )

    def submit_sell(
        self,
        symbol: str,
        shares: int,
        note: Optional[str] = None,
    ) -> OrderResult:
        pos = self._state["positions"].get(symbol)
        if not pos:
            return OrderResult(
                symbol=symbol,
                action="SELL",
                shares=0,
                filled_price=0.0,
                success=False,
                error=f"No position in {symbol}",
            )

        price = self.get_last_price(symbol)
        if price is None:
            price = pos["avg_entry_price"]

        sell_shares = min(shares, pos["shares"])
        proceeds = sell_shares * price
        self._state["cash"] += proceeds

        if sell_shares >= pos["shares"]:
            del self._state["positions"][symbol]
        else:
            self._state["positions"][symbol]["shares"] -= sell_shares

        self._persist()
        pnl = (price - pos["avg_entry_price"]) * sell_shares
        logger.info("PaperBroker SELL %s    '         %d @ %.4f  PnL=%.2f", symbol, sell_shares, price, pnl)
        return OrderResult(
            symbol=symbol,
            action="SELL",
            shares=sell_shares,
            filled_price=price,
            cost=proceeds,
            success=True,
        )

    @property
    def raw_positions(self) -> Dict[str, Any]:
        return dict(self._state["positions"])
