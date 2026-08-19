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


class BacktestResult(Base):
    """Stored metrics from a backtest run."""

    __tablename__ = "backtest_results"

    id                = Column(Integer,    primary_key=True, index=True)
    period_name       = Column(String(32), nullable=False, index=True)
    start_date        = Column(Date,       nullable=False)
    end_date          = Column(Date,       nullable=False)
    cagr              = Column(Float,      nullable=True)
    max_drawdown      = Column(Float,      nullable=True)
    sharpe            = Column(Float,      nullable=True)
    sortino           = Column(Float,      nullable=True)
    profit_factor     = Column(Float,      nullable=True)
    win_rate          = Column(Float,      nullable=True)
    avg_win           = Column(Float,      nullable=True)
    avg_loss          = Column(Float,      nullable=True)
    total_trades      = Column(Integer,    nullable=True)
    avg_holding_days  = Column(Float,      nullable=True)
    final_equity      = Column(Float,      nullable=True)
    equity_curve      = Column(JSON,       nullable=True)
    per_symbol_metrics = Column(JSON,      nullable=True)
    parameters        = Column(JSON,       nullable=True)
    created_at        = Column(DateTime,   default=datetime.utcnow)


class RobustnessResult(Base):
    """Results from parameter perturbation / market-removal tests."""

    __tablename__ = "robustness_results"

    id          = Column(Integer,     primary_key=True, index=True)
    test_type   = Column(String(32),  nullable=False)
    test_label  = Column(String(128), nullable=False)
    period_name = Column(String(32),  nullable=False)
    cagr        = Column(Float,       nullable=True)
    max_drawdown = Column(Float,      nullable=True)
    sharpe      = Column(Float,       nullable=True)
    profit_factor = Column(Float,     nullable=True)
    total_trades = Column(Integer,    nullable=True)
    parameters  = Column(JSON,        nullable=True)
    created_at  = Column(DateTime,    default=datetime.utcnow)


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