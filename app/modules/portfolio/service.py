"""Portfolio service                    business logic and persistence."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from paper_signs_backend.app.broker.base import BaseBroker
from paper_signs_backend.app.models.database import SessionLocal
from paper_signs_backend.app.models.orm import PortfolioSnapshot
from paper_signs_backend.app.modules.portfolio.schemas import EquityPoint, PortfolioOut, PositionOut


def get_live_portfolio(broker: BaseBroker) -> PortfolioOut:
    """Return live portfolio state from the broker."""
    account = broker.get_account()
    positions = [
        PositionOut(
            symbol=p.symbol,
            shares=p.shares,
            avg_entry_price=p.avg_entry_price,
            current_price=p.current_price,
            unrealized_pnl=p.unrealized_pnl,
            entry_date=p.entry_date,
            market_value=(p.current_price or p.avg_entry_price) * p.shares,
        )
        for p in account.positions
    ]
    return PortfolioOut(
        equity=account.equity,
        cash=account.cash,
        positions=positions,
        snapshot_date=date.today().isoformat(),
    )


def get_equity_history(db: Session, limit: int = 365) -> List[EquityPoint]:
    """Return historical portfolio equity curve."""
    rows = (
        db.query(PortfolioSnapshot)
        .order_by(PortfolioSnapshot.snapshot_date.asc())
        .limit(limit)
        .all()
    )
    return [EquityPoint(date=r.snapshot_date.isoformat(), equity=r.equity) for r in rows]


def get_snapshots(db: Session, limit: int = 30) -> List[Dict[str, Any]]:
    """Return raw portfolio snapshots with position detail."""
    rows = (
        db.query(PortfolioSnapshot)
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .limit(limit)
        .all()
    )
    return [
        {"date": r.snapshot_date.isoformat(), "equity": r.equity, "cash": r.cash, "positions": r.positions}
        for r in rows
    ]


def upsert_snapshot(
    db: Session,
    snapshot_date: date,
    equity: float,
    cash: float,
    positions: Dict[str, Any],
) -> PortfolioSnapshot:
    """Insert or update today''s portfolio snapshot."""
    existing = (
        db.query(PortfolioSnapshot)
        .filter(PortfolioSnapshot.snapshot_date == snapshot_date)
        .first()
    )
    if existing:
        existing.equity = equity
        existing.cash = cash
        existing.positions = positions
        db.commit()
        db.refresh(existing)
        return existing
    snap = PortfolioSnapshot(snapshot_date=snapshot_date, equity=equity, cash=cash, positions=positions)
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap