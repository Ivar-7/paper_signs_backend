"""Backtest service                    orchestrates engine runs and persistence."""

from __future__ import annotations

from datetime import date
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from paper_signs_backend.app.backtest.engine import (
    BacktestEngine,
    run_cost_stress,
    run_market_removal,
    run_parameter_perturbation,
)
from paper_signs_backend.app.data.market import get_all_symbols
from paper_signs_backend.app.exceptions import NotFoundError, ServiceError
from paper_signs_backend.app.models.orm import BacktestResult, RobustnessResult
from paper_signs_backend.app.strategy.constants import BACKTEST_PERIODS

logger = logging.getLogger(__name__)


def _to_date(d: Any) -> date:
    if isinstance(d, date):
        return d
    return date.fromisoformat(str(d))


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _to_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _persist_backtest(result, db: Session) -> None:
    """Write a BacktestResult dataclass to the database."""
    row = BacktestResult(
        period_name=result.period_name,
        start_date=_to_date(result.start_date),
        end_date=_to_date(result.end_date),
        cagr=_to_float(result.cagr),
        max_drawdown=_to_float(result.max_drawdown),
        sharpe=_to_float(result.sharpe),
        sortino=_to_float(result.sortino),
        profit_factor=_to_float(result.profit_factor),
        win_rate=_to_float(result.win_rate),
        avg_win=_to_float(result.avg_win),
        avg_loss=_to_float(result.avg_loss),
        total_trades=_to_int(result.total_trades),
        avg_holding_days=_to_float(result.avg_holding_days),
        final_equity=_to_float(result.final_equity),
        equity_curve=result.equity_curve,
        per_symbol_metrics=result.per_symbol,
        parameters=result.parameters,
    )
    db.add(row)
    db.commit()


def _persist_robustness(rows: List[Dict], test_type: str, period_name: str, db: Session) -> None:
    for row in rows:
        db.add(RobustnessResult(
            test_type=test_type,
            test_label=row["test_label"],
            period_name=period_name,
            cagr=_to_float(row.get("cagr")),
            max_drawdown=_to_float(row.get("max_drawdown")),
            sharpe=_to_float(row.get("sharpe")),
            profit_factor=_to_float(row.get("profit_factor")),
            total_trades=_to_int(row.get("total_trades")),
            parameters=row,
        ))
    db.commit()


def run_backtest(
    period: str,
    commission: float,
    db: Session,
) -> List[Dict[str, Any]]:
    """Run one or all backtest periods; persist results; return summary."""
    periods_to_run = ["dev", "validation", "oos"] if period == "all" else [period]

    if period != "all" and period not in BACKTEST_PERIODS:
        raise NotFoundError(f"Unknown period: {period!r}")

    logger.info("Pre-fetching market data...")
    try:
        all_data = get_all_symbols()
    except Exception as exc:
        raise ServiceError(f"Market data unavailable: {exc}") from exc

    engine = BacktestEngine(commission_pct=commission)
    results = []

    for p_name in periods_to_run:
        start, end = BACKTEST_PERIODS[p_name]
        try:
            result = engine.run(period_name=p_name, start=start, end=end, market_data=all_data)
            _persist_backtest(result, db)
            results.append({
                "period": p_name,
                "start": result.start_date,
                "end": result.end_date,
                "cagr": f"{result.cagr * 100:.2f}%",
                "max_drawdown": f"{result.max_drawdown * 100:.2f}%",
                "sharpe": result.sharpe,
                "profit_factor": result.profit_factor,
                "total_trades": result.total_trades,
                "final_equity": result.final_equity,
            })
        except (NotFoundError, ServiceError):
            raise
        except Exception as exc:
            logger.error("Backtest failed for %s: %s", p_name, exc)
            results.append({"period": p_name, "error": "Backtest computation failed"})

    return results


def get_results(db: Session) -> List[BacktestResult]:
    """Return the most recent result for each period."""
    results = []
    for period in ("dev", "validation", "oos"):
        row = (
            db.query(BacktestResult)
            .filter(BacktestResult.period_name == period)
            .order_by(BacktestResult.created_at.desc())
            .first()
        )
        if row:
            results.append(row)
    return results


def get_equity_curve(period_name: str, db: Session) -> Dict[str, Any]:
    """Return equity curve for the most recent run of a period."""
    row = (
        db.query(BacktestResult)
        .filter(BacktestResult.period_name == period_name)
        .order_by(BacktestResult.created_at.desc())
        .first()
    )
    if not row:
        raise NotFoundError(f"No backtest found for period {period_name!r}")
    return {"period_name": period_name, "equity_curve": row.equity_curve}


def run_robustness(
    test_type: str,
    period: str,
    db: Session,
) -> List[Dict[str, Any]]:
    """Run robustness tests and persist results."""
    try:
        all_data = get_all_symbols()
    except Exception as exc:
        raise ServiceError(f"Market data unavailable: {exc}") from exc

    all_results: List[Dict] = []

    if test_type in ("perturbation", "all"):
        rows = run_parameter_perturbation(period_name=period, market_data=all_data)
        _persist_robustness(rows, "perturbation", period, db)
        all_results.extend(rows)

    if test_type in ("market_removal", "all"):
        rows = run_market_removal(period_name=period, market_data=all_data)
        _persist_robustness(rows, "market_removal", period, db)
        all_results.extend(rows)

    if test_type in ("cost_stress", "all"):
        rows = run_cost_stress(period_name=period, market_data=all_data)
        _persist_robustness(rows, "cost_stress", period, db)
        all_results.extend(rows)

    return all_results


def get_robustness_results(
    test_type: Optional[str],
    db: Session,
) -> List[RobustnessResult]:
    """Return stored robustness results."""
    q = db.query(RobustnessResult)
    if test_type:
        q = q.filter(RobustnessResult.test_type == test_type)
    return q.order_by(RobustnessResult.created_at.desc()).limit(500).all()