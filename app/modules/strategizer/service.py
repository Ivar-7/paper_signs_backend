"""Strategizer service backed directly by SQLite."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from paper_signs_backend.app.config import get_settings
from paper_signs_backend.app.data.market import get_ohlcv
from paper_signs_backend.app.models.database import SessionLocal
from paper_signs_backend.app.models.orm import TrackedSymbol
from paper_signs_backend.app.strategy import engine

logger = logging.getLogger(__name__)
settings = get_settings()

DEFAULT_SYMBOLS = [
    "SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "GLD", "DBC", "VNQ", "UUP",
]


def _init_default_symbols(db) -> List[str]:
    """Ensure baseline tracked symbols exist in database."""
    existing = db.query(TrackedSymbol).all()
    if not existing:
        base_list = settings.symbol_list or DEFAULT_SYMBOLS
        for sym in base_list:
            clean = sym.upper().strip()
            db.add(TrackedSymbol(symbol=clean, is_active=True))
        db.commit()
        return base_list
    return [r.symbol for r in existing if r.is_active]


def get_tracked_symbols() -> List[str]:
    db = SessionLocal()
    try:
        syms = _init_default_symbols(db)
        return sorted(syms)
    finally:
        db.close()


def add_tracked_symbol(symbol: str) -> bool:
    clean = symbol.upper().strip()
    if not clean:
        return False

    # Validate symbol with market provider
    try:
        df = get_ohlcv(clean, period="1mo")
        if df.empty:
            return False
    except Exception:
        return False

    db = SessionLocal()
    try:
        existing = db.query(TrackedSymbol).filter(TrackedSymbol.symbol == clean).first()
        if existing:
            existing.is_active = True
        else:
            db.add(TrackedSymbol(symbol=clean, is_active=True))
        db.commit()
        return True
    finally:
        db.close()


def remove_tracked_symbol(symbol: str) -> bool:
    clean = symbol.upper().strip()
    db = SessionLocal()
    try:
        existing = db.query(TrackedSymbol).filter(TrackedSymbol.symbol == clean).first()
        if existing:
            db.delete(existing)
            db.commit()
            return True
        return False
    finally:
        db.close()


def scan_markets(force_refresh: bool = False) -> Dict[str, Any]:
    symbols = get_tracked_symbols()
    return engine.scan_all_markets(symbols=symbols, force_refresh=force_refresh)


def get_symbol_analysis(symbol: str) -> Optional[Dict[str, Any]]:
    return engine.get_symbol_analysis(symbol.upper().strip())
