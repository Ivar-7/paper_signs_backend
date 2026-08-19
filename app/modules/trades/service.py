"""Trades service — business logic and persistence."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from paper_signs_backend.app.models.orm import Trade
from paper_signs_backend.app.modules.trades.schemas import TradeSummary


def get_trades(
    db: Session,
    symbol: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Trade]:
    """Return paginated trade history with optional filters."""
    q = db.query(Trade)
    if symbol:
        q = q.filter(Trade.symbol == symbol.upper())
    if action:
        q = q.filter(Trade.action == action.upper())
    return q.order_by(Trade.trade_date.desc()).offset(offset).limit(limit).all()


def get_summary(db: Session) -> TradeSummary:
    """Return aggregate trade statistics."""
    rows = db.query(Trade).all()
    if not rows:
        return TradeSummary(total_trades=0, total_pnl=0.0, wins=0, losses=0, win_rate=0.0)

    total_pnl = sum(t.pnl or 0 for t in rows)
    wins = sum(1 for t in rows if (t.pnl or 0) > 0)
    losses = len(rows) - wins
    return TradeSummary(
        total_trades=len(rows),
        total_pnl=round(total_pnl, 2),
        wins=wins,
        losses=losses,
        win_rate=round(wins / len(rows) * 100, 1),
    )


def insert_trade(
    db: Session,
    *,
    trade_date: date,
    symbol: str,
    action: str,
    shares: int,
    price: float,
    cost: float,
    pnl: float = 0.0,
    broker_order_id: Optional[str] = None,
) -> Trade:
    """Persist a new trade record."""
    trade = Trade(
        trade_date=trade_date,
        symbol=symbol,
        action=action,
        shares=shares,
        price=price,
        cost=cost,
        pnl=pnl,
        broker_order_id=broker_order_id,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade