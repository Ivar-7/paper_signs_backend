"""Abstract broker interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class OrderResult:
    symbol: str
    action: str          # BUY | SELL
    shares: int
    filled_price: float
    order_id: Optional[str] = None
    cost: float = 0.0
    success: bool = True
    error: Optional[str] = None


@dataclass
class BrokerPosition:
    symbol: str
    shares: int
    avg_entry_price: float
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    entry_date: Optional[str] = None


@dataclass
class BrokerAccount:
    equity: float
    cash: float
    positions: List[BrokerPosition]


class BaseBroker(ABC):
    """All broker implementations must implement this interface."""

    @abstractmethod
    def get_account(self) -> BrokerAccount:
        """Return current account equity, cash, and positions."""

    @abstractmethod
    def submit_buy(
        self,
        symbol: str,
        shares: int,
        note: Optional[str] = None,
    ) -> OrderResult:
        """Submit a market buy order for *shares* of *symbol*."""

    @abstractmethod
    def submit_sell(
        self,
        symbol: str,
        shares: int,
        note: Optional[str] = None,
    ) -> OrderResult:
        """Submit a market sell order for all *shares* of *symbol*."""

    @abstractmethod
    def get_last_price(self, symbol: str) -> Optional[float]:
        """Return the most recent available price for *symbol*."""
