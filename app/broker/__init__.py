"""
Broker factory    '                                   returns the configured broker instance.
"""

from __future__ import annotations

from paper_signs_backend.app.broker.base import BaseBroker
from paper_signs_backend.app.config import get_settings

_broker_instance: BaseBroker | None = None


def get_broker() -> BaseBroker:
    """Return the singleton broker instance for the configured backend."""
    global _broker_instance
    if _broker_instance is None:
        settings = get_settings()
        if settings.broker == "alpaca":
            from paper_signs_backend.app.broker.alpaca import AlpacaBroker
            _broker_instance = AlpacaBroker()
        else:
            from paper_signs_backend.app.broker.paper import PaperBroker
            _broker_instance = PaperBroker()
    return _broker_instance
