"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, Integer,
    JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class PaperAccount(Base):
    """Simulated broker account cash state."""

    __tablename__ = "paper_account"

    id = Column(Integer, primary_key=True)
    cash = Column(Float, nullable=False, default=100000.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaperPosition(Base):
    """Simulated broker open positions."""

    __tablename__ = "paper_positions"

    symbol = Column(String(16), primary_key=True)
    shares = Column(Integer, nullable=False)
    avg_entry_price = Column(Float, nullable=False)
    entry_date = Column(String(16), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TrackedSymbol(Base):
    """Dynamically tracked market instruments."""

    __tablename__ = "tracked_symbols"

    symbol = Column(String(16), primary_key=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PortfolioSnapshot(Base):
    """Daily snapshot of portfolio equity, cash, and positions."""

    __tablename__ = "portfolio_snapshots"

    id            = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(Date,    nullable=False, index=True, unique=True)
    equity        = Column(Float,   nullable=False)
    cash          = Column(Float,   nullable=False)
    positions     = Column(JSON,    nullable=False, default=dict)
    created_at    = Column(DateTime, default=datetime.utcnow)


class Trade(Base):
    """Record of every buy/sell executed."""

    __tablename__ = "trades"

    id              = Column(Integer,     primary_key=True, index=True)
    trade_date      = Column(Date,        nullable=False, index=True)
    symbol          = Column(String(16),  nullable=False, index=True)
    action          = Column(String(4),   nullable=False)
    shares          = Column(Integer,     nullable=False)
    price           = Column(Float,       nullable=False)
    cost            = Column(Float,       nullable=False)
    pnl             = Column(Float,       nullable=True)
    broker_order_id = Column(String(64),  nullable=True)
    created_at      = Column(DateTime,    default=datetime.utcnow)


class Signal(Base):
    """Generated signal for a symbol on a given date."""

    __tablename__ = "signals"

    id               = Column(Integer,    primary_key=True, index=True)
    signal_date      = Column(Date,       nullable=False, index=True)
    symbol           = Column(String(16), nullable=False, index=True)
    close            = Column(Float,      nullable=True)
    entry_high       = Column(Float,      nullable=True)
    exit_low         = Column(Float,      nullable=True)
    sma200           = Column(Float,      nullable=True)
    atr20            = Column(Float,      nullable=True)
    entry_signal     = Column(Boolean,    nullable=False, default=False)
    exit_signal      = Column(Boolean,    nullable=False, default=False)
    suggested_shares = Column(Integer,    nullable=True)
    suggested_cost   = Column(Float,      nullable=True)
    created_at       = Column(DateTime,   default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("signal_date", "symbol", name="uq_signal_date_symbol"),
    )


class SchedulerRun(Base):
    """Log of each daily scheduler execution."""

    __tablename__ = "scheduler_runs"

    id               = Column(Integer,    primary_key=True, index=True)
    run_date         = Column(Date,       nullable=False, index=True)
    status           = Column(String(16), nullable=False)
    message          = Column(Text,       nullable=True)
    duration_seconds = Column(Float,      nullable=True)
    trades_executed  = Column(Integer,    nullable=True)
    created_at       = Column(DateTime,   default=datetime.utcnow)