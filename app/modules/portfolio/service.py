"""Portfolio service - business logic and persistence."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from paper_signs_backend.app.broker.base import BaseBroker
from paper_signs_backend.app.models.orm import PortfolioSnapshot
from paper_signs_backend.app.modules.portfolio.schemas import EquityPoint, PortfolioOut, PositionOut
from paper_signs_backend.app.modules.trades.service import insert_trade


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


def close_position(broker: BaseBroker, db: Session, symbol: str) -> Dict[str, Any]:
    """Close an open position for symbol, calculate realized PnL, and record SELL trade."""
    clean_sym = symbol.upper().strip()
    account = broker.get_account()
    pos = next((p for p in account.positions if p.symbol == clean_sym), None)
    if not pos:
        return {"success": False, "message": f"No open position found for {clean_sym}"}

    res = broker.submit_sell(symbol=clean_sym, shares=pos.shares, note="Manual Close via UI")
    if not res.success:
        return {"success": False, "message": res.error or "Failed to close position"}

    pnl = (res.filled_price - pos.avg_entry_price) * res.shares
    insert_trade(
        db=db,
        trade_date=date.today(),
        symbol=clean_sym,
        action="SELL",
        shares=res.shares,
        price=res.filled_price,
        cost=res.cost,
        pnl=round(pnl, 2),
        broker_order_id=res.order_id,
    )

    return {
        "success": True,
        "symbol": clean_sym,
        "shares": res.shares,
        "price": res.filled_price,
        "pnl": round(pnl, 2),
        "message": f"Closed {clean_sym} position ({res.shares} shares @ ${res.filled_price:.2f}, PnL: ${pnl:+.2f})",
    }


def reset_portfolio(broker: BaseBroker, db: Session, initial_capital: float = 100_000.0) -> Dict[str, Any]:
    """Reset paper account balance and clear snapshots/positions."""
    broker.reset_account(initial_capital=initial_capital)
    # Save a fresh baseline snapshot
    upsert_snapshot(
        db=db,
        snapshot_date=date.today(),
        equity=initial_capital,
        cash=initial_capital,
        positions={},
    )
    return {
        "success": True,
        "message": f"Account reset to ${initial_capital:,.2f}",
        "equity": initial_capital,
        "cash": initial_capital,
    }


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
    """Insert or update today's portfolio snapshot."""
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