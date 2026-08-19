"""System Pydantic schemas."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class StatusResponse(BaseModel):
    status: str
    scheduler_running: bool
    next_run: Optional[str]
    broker: str
    symbols: List[str]
    version: str
    timestamp: str