"""Signals router — HTTP concerns only."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from paper_signs_backend.app.dependencies.db import get_db
from paper_signs_backend.app.modules.signals import service
from paper_signs_backend.app.modules.signals.schemas import SignalOut

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/", response_model=List[SignalOut])
def get_latest_signals(db: Session = Depends(get_db)) -> List[SignalOut]:
    """Return today''s signals for all instruments."""
    return service.get_latest_signals(db)


@router.get("/history", response_model=List[SignalOut])
def get_signal_history(
    symbol: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
) -> List[SignalOut]:
    """Return recent signals, optionally filtered by symbol."""
    return service.get_signal_history(db, symbol=symbol, limit=limit)