"""
Internal paper trading simulation broker backed by SQLite.

No external API or JSON state files required. State is persisted directly via the database.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from paper_signs_backend.app.broker.base import BaseBroker, BrokerAccount, BrokerPosition, OrderResult
from paper_signs_backend.app.config import get_settings
from paper_signs_backend.app.data.market import get_ohlcv
from paper_signs_backend.app.models.database import SessionLocal
from paper_signs_backend.app.models.orm import PaperAccount, PaperPosition
from paper_signs_backend.app.strategy.constants import INITIAL_CAPITAL

logger = logging.getLogger(__name__)
settings = get_settings()


class PaperBroker(BaseBroker):
    """Zero-cost paper trading simulator backed directly by SQLite."""

    def _get_or_create_account(self, db) -> PaperAccount:
        acc = db.query(PaperAccount).first()
        if not acc:
            acc = PaperAccount(id=1, cash=INITIAL_CAPITAL)
            db.add(acc)
            db.commit()
            db.refresh(acc)
        return acc

    def reset_account(self, initial_capital: float = INITIAL_CAPITAL) -> None:
        db = SessionLocal()
        try:
            acc = self._get_or_create_account(db)
            acc.cash = initial_capital
            db.query(PaperPosition).delete()
            db.commit()
            logger.info("PaperBroker: Account reset to $%.2f in SQLite", initial_capital)
        finally:
            db.close()

    def get_last_price(self, symbol: str) -> Optional[float]:
        try:
            df = get_ohlcv(symbol, period="5d")
            return float(df["Close"].iloc[-1])
        except Exception as exc:
            logger.error("PaperBroker: failed to fetch price for %s: %s", symbol, exc)
            return None

    def get_account(self) -> BrokerAccount:
        db = SessionLocal()
        try:
            acc = self._get_or_create_account(db)
            pos_rows = db.query(PaperPosition).all()

            positions: List[BrokerPosition] = []
            total_market_value = 0.0

            for p in pos_rows:
                price = self.get_last_price(p.symbol)
                mkt_val = (price or p.avg_entry_price) * p.shares
                total_market_value += mkt_val
                unrealized = (
                    ((price - p.avg_entry_price) * p.shares)
                    if price is not None
                    else None
                )
                positions.append(
                    BrokerPosition(
                        symbol=p.symbol,
                        shares=p.shares,
                        avg_entry_price=p.avg_entry_price,
                        current_price=price,
                        unrealized_pnl=unrealized,
                        entry_date=p.entry_date,
                    )
                )

            equity = acc.cash + total_market_value
            return BrokerAccount(
                equity=equity,
                cash=acc.cash,
                positions=positions,
            )
        finally:
            db.close()

    def submit_buy(
        self,
        symbol: str,
        shares: int,
        note: Optional[str] = None,
    ) -> OrderResult:
        clean_sym = symbol.upper().strip()
        price = self.get_last_price(clean_sym)
        if price is None:
            return OrderResult(
                symbol=clean_sym,
                action="BUY",
                shares=shares,
                filled_price=0.0,
                success=False,
                error="Could not fetch price",
            )

        db = SessionLocal()
        try:
            acc = self._get_or_create_account(db)
            cost = shares * price
            if cost > acc.cash:
                shares = int(acc.cash // price)
                cost = shares * price
                if shares <= 0:
                    return OrderResult(
                        symbol=clean_sym,
                        action="BUY",
                        shares=0,
                        filled_price=price,
                        success=False,
                        error="Insufficient cash",
                    )

            acc.cash -= cost

            existing = db.query(PaperPosition).filter(PaperPosition.symbol == clean_sym).first()
            if existing:
                total_shares = existing.shares + shares
                avg_price = (
                    (existing.shares * existing.avg_entry_price + shares * price)
                    / total_shares
                )
                existing.shares = total_shares
                existing.avg_entry_price = round(avg_price, 4)
            else:
                new_pos = PaperPosition(
                    symbol=clean_sym,
                    shares=shares,
                    avg_entry_price=round(price, 4),
                    entry_date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                )
                db.add(new_pos)

            db.commit()
            logger.info("PaperBroker BUY %s - %d @ %.4f (SQLite)", clean_sym, shares, price)
            return OrderResult(
                symbol=clean_sym,
                action="BUY",
                shares=shares,
                filled_price=price,
                cost=cost,
                success=True,
            )
        finally:
            db.close()

    def submit_sell(
        self,
        symbol: str,
        shares: int,
        note: Optional[str] = None,
    ) -> OrderResult:
        clean_sym = symbol.upper().strip()
        db = SessionLocal()
        try:
            pos = db.query(PaperPosition).filter(PaperPosition.symbol == clean_sym).first()
            if not pos:
                return OrderResult(
                    symbol=clean_sym,
                    action="SELL",
                    shares=0,
                    filled_price=0.0,
                    success=False,
                    error=f"No position in {clean_sym}",
                )

            price = self.get_last_price(clean_sym)
            if price is None:
                price = pos.avg_entry_price

            sell_shares = min(shares, pos.shares)
            proceeds = sell_shares * price

            acc = self._get_or_create_account(db)
            acc.cash += proceeds

            pnl = (price - pos.avg_entry_price) * sell_shares

            if sell_shares >= pos.shares:
                db.delete(pos)
            else:
                pos.shares -= sell_shares

            db.commit()
            logger.info("PaperBroker SELL %s - %d @ %.4f PnL=%.2f (SQLite)", clean_sym, sell_shares, price, pnl)
            return OrderResult(
                symbol=clean_sym,
                action="SELL",
                shares=sell_shares,
                filled_price=price,
                cost=proceeds,
                success=True,
            )
        finally:
            db.close()
