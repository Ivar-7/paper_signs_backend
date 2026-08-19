"""
Alpaca paper trading broker.

Uses the alpaca-py SDK to interact with Alpaca's paper trading endpoint.
Requires ALPACA_API_KEY and ALPACA_SECRET_KEY in .env.
"""

from __future__ import annotations

import logging
from typing import Optional

from paper_signs_backend.app.broker.base import BaseBroker, BrokerAccount, BrokerPosition, OrderResult
from paper_signs_backend.app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AlpacaBroker(BaseBroker):
    """Alpaca paper trading broker via alpaca-py SDK."""

    def __init__(self) -> None:
        from alpaca.trading.client import TradingClient
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestQuoteRequest

        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            raise ValueError(
                "ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env "
                "when BROKER=alpaca"
            )

        # paper=True routes to paper-api.alpaca.markets
        self._client = TradingClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            paper=True,
        )
        self._data_client = StockHistoricalDataClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
        )
        self._LatestQuoteRequest = StockLatestQuoteRequest

    def get_last_price(self, symbol: str) -> Optional[float]:
        try:
            req = self._LatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self._data_client.get_stock_latest_quote(req)
            quote = quotes[symbol]
            # Use midpoint of ask/bid
            return round((quote.ask_price + quote.bid_price) / 2, 4)
        except Exception as exc:
            logger.error("Alpaca price fetch failed for %s: %s", symbol, exc)
            return None

    def get_account(self) -> BrokerAccount:
        from alpaca.trading.requests import GetAssetsRequest

        account = self._client.get_account()
        positions_raw = self._client.get_all_positions()

        positions = [
            BrokerPosition(
                symbol=p.symbol,
                shares=int(p.qty),
                avg_entry_price=float(p.avg_entry_price),
                current_price=float(p.current_price) if p.current_price else None,
                unrealized_pnl=float(p.unrealized_pl) if p.unrealized_pl else None,
            )
            for p in positions_raw
        ]

        return BrokerAccount(
            equity=float(account.equity),
            cash=float(account.cash),
            positions=positions,
        )

    def submit_buy(
        self,
        symbol: str,
        shares: int,
        note: Optional[str] = None,
    ) -> OrderResult:
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        try:
            request = MarketOrderRequest(
                symbol=symbol,
                qty=shares,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
            )
            order = self._client.submit_order(request)
            logger.info("Alpaca BUY order submitted: %s × %d  id=%s", symbol, shares, order.id)
            return OrderResult(
                symbol=symbol,
                action="BUY",
                shares=shares,
                filled_price=float(order.filled_avg_price or 0),
                order_id=str(order.id),
                success=True,
            )
        except Exception as exc:
            logger.error("Alpaca BUY failed for %s: %s", symbol, exc)
            return OrderResult(
                symbol=symbol,
                action="BUY",
                shares=shares,
                filled_price=0.0,
                success=False,
                error=str(exc),
            )

    def submit_sell(
        self,
        symbol: str,
        shares: int,
        note: Optional[str] = None,
    ) -> OrderResult:
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        try:
            request = MarketOrderRequest(
                symbol=symbol,
                qty=shares,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
            )
            order = self._client.submit_order(request)
            logger.info("Alpaca SELL order submitted: %s × %d  id=%s", symbol, shares, order.id)
            return OrderResult(
                symbol=symbol,
                action="SELL",
                shares=shares,
                filled_price=float(order.filled_avg_price or 0),
                order_id=str(order.id),
                success=True,
            )
        except Exception as exc:
            logger.error("Alpaca SELL failed for %s: %s", symbol, exc)
            return OrderResult(
                symbol=symbol,
                action="SELL",
                shares=shares,
                filled_price=0.0,
                success=False,
                error=str(exc),
            )
