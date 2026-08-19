"""Signals service                    business logic and persistence."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from paper_signs_backend.app.models.orm import Signal
from paper_signs_backend.app.modules.signals.schemas import SignalOut


def get_latest_signals(db: Session) -> List[SignalOut]:
    """Return all signals for the most recent signal date."""
    latest_date = (
        db.query(Signal.signal_date)
        .order_by(Signal.signal_date.desc())
        .first()
    )
    if not latest_date:
        return []
    rows = (
        db.query(Signal)
        .filter(Signal.signal_date == latest_date[0])
        .order_by(Signal.symbol)
        .all()
    )
    return [SignalOut.model_validate(r) for r in rows]


def get_signal_history(
    db: Session,
    symbol: Optional[str] = None,
    limit: int = 100,
) -> List[SignalOut]:
    """Return recent signals, optionally filtered by symbol."""
    q = db.query(Signal)
    if symbol:
        q = q.filter(Signal.symbol == symbol.upper())
    rows = q.order_by(Signal.signal_date.desc()).limit(limit).all()
    return [SignalOut.model_validate(r) for r in rows]


def upsert_signal(
    db: Session,
    *,
    signal_date: date,
    symbol: str,
    close: Optional[float],
    entry_high: Optional[float],
    exit_low: Optional[float],
    sma200: Optional[float],
    atr20: Optional[float],
    entry_signal: bool,
    exit_signal: bool,
    suggested_shares: Optional[int] = None,
    suggested_cost: Optional[float] = None,
) -> Signal:
    """Insert or update a signal record."""
    existing = (
        db.query(Signal)
        .filter(Signal.signal_date == signal_date, Signal.symbol == symbol)
        .first()
    )
    data = dict(
        close=close, entry_high=entry_high, exit_low=exit_low,
        sma200=sma200, atr20=atr20, entry_signal=entry_signal,
        exit_signal=exit_signal, suggested_shares=suggested_shares,
        suggested_cost=suggested_cost,
    )
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing
    sig = Signal(signal_date=signal_date, symbol=symbol, **data)
    db.add(sig)
    db.commit()
    db.refresh(sig)
    return sig