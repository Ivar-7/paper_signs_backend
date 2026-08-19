"""Shared database session dependency."""

from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from paper_signs_backend.app.models.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and guarantee cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()