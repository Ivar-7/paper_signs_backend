"""Strategizer router - HTTP endpoints for live market scanning and strategy intelligence."""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query

from paper_signs_backend.app.modules.strategizer import service
from paper_signs_backend.app.modules.strategizer.schemas import (
    AddSymbolRequest,
    StrategizerScanResponse,
    SymbolItem,
)

router = APIRouter(prefix="/api/strategizer", tags=["strategizer"])


@router.get("/scan", response_model=StrategizerScanResponse)
def scan_markets(force_refresh: bool = Query(False)) -> Dict[str, Any]:
    """
    Execute full strategy scan across all tracked instruments.
    Returns ranked opportunities sorted by probability percentage.
    """
    return service.scan_markets(force_refresh=force_refresh)


@router.get("/analysis/{symbol}")
def get_symbol_analysis(symbol: str) -> Dict[str, Any]:
    """
    Get deep-dive strategy analysis and indicators chart series for a specific symbol.
    """
    res = service.get_symbol_analysis(symbol)
    if not res:
        raise HTTPException(status_code=404, detail=f"Market data not available for symbol '{symbol}'")
    return res


@router.get("/symbols", response_model=List[str])
def get_tracked_symbols() -> List[str]:
    """Get list of all currently tracked market symbols."""
    return service.get_tracked_symbols()


@router.post("/symbols")
def add_symbol(payload: AddSymbolRequest) -> Dict[str, Any]:
    """Add a new symbol to the tracked universe."""
    success = service.add_tracked_symbol(payload.symbol)
    if not success:
        raise HTTPException(status_code=400, detail=f"Invalid or unsupported symbol '{payload.symbol}'")
    return {"status": "ok", "symbol": payload.symbol.upper(), "symbols": service.get_tracked_symbols()}


@router.delete("/symbols/{symbol}")
def remove_symbol(symbol: str) -> Dict[str, Any]:
    """Remove a symbol from the tracked universe."""
    success = service.remove_tracked_symbol(symbol)
    if not success:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' was not found in tracked list")
    return {"status": "ok", "removed": symbol.upper(), "symbols": service.get_tracked_symbols()}
