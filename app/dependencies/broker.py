"""Shared broker dependency."""

from __future__ import annotations

from paper_signs_backend.app.broker import get_broker
from paper_signs_backend.app.broker.base import BaseBroker


def get_broker_dep() -> BaseBroker:
    """Return the configured broker singleton."""
    return get_broker()