"""Backtest router — HTTP concerns only."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from paper_signs_backend.app.dependencies.db import get_db
from paper_signs_backend.app.modules.backtest import service
from paper_signs_backend.app.modules.backtest.schemas import BacktestResultOut, RobustnessResultOut

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.get("/results")
def get_backtest_results(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Return the most recent backtest result for each period."""
    rows = service.get_results(db)
    return [
        {
            "id": r.id,
            "period_name": r.period_name,
            "start_date": str(r.start_date),
            "end_date": str(r.end_date),
            "cagr": r.cagr,
            "max_drawdown": r.max_drawdown,
            "sharpe": r.sharpe,
            "sortino": r.sortino,
            "profit_factor": r.profit_factor,
            "win_rate": r.win_rate,
            "avg_win": r.avg_win,
            "avg_loss": r.avg_loss,
            "total_trades": r.total_trades,
            "avg_holding_days": r.avg_holding_days,
            "final_equity": r.final_equity,
            "per_symbol_metrics": r.per_symbol_metrics,
            "parameters": r.parameters,
            "created_at": str(r.created_at),
        }
        for r in rows
    ]


@router.get("/equity-curve/{period_name}")
def get_equity_curve(
    period_name: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return the equity curve for the most recent run of a period."""
    return service.get_equity_curve(period_name, db)


@router.post("/run")
def run_backtest(
    period: str = Query("all", description="dev | validation | oos | all"),
    commission: float = Query(0.001, description="Commission per side"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Trigger a backtest run. Blocks until complete."""
    results = service.run_backtest(period=period, commission=commission, db=db)
    return {"status": "complete", "results": results}


@router.post("/robustness")
def run_robustness(
    test_type: str = Query("all", description="perturbation | market_removal | cost_stress | all"),
    period: str = Query("validation"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Run robustness tests."""
    results = service.run_robustness(test_type=test_type, period=period, db=db)
    return {"status": "complete", "count": len(results), "results": results}


@router.get("/robustness")
def get_robustness_results(
    test_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return stored robustness test results."""
    rows = service.get_robustness_results(test_type=test_type, db=db)
    return [
        {
            "id": r.id,
            "test_type": r.test_type,
            "test_label": r.test_label,
            "period_name": r.period_name,
            "cagr": r.cagr,
            "max_drawdown": r.max_drawdown,
            "sharpe": r.sharpe,
            "profit_factor": r.profit_factor,
            "total_trades": r.total_trades,
            "created_at": str(r.created_at),
        }
        for r in rows
    ]