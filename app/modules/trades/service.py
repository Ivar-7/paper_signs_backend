"""Trades service - business logic, execution, and persistence."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from paper_signs_backend.app.broker import get_broker
from paper_signs_backend.app.data.market import get_ohlcv
from paper_signs_backend.app.models.orm import Trade
from paper_signs_backend.app.modules.trades.schemas import ExecuteTradeResponse, TradeSummary
from paper_signs_backend.app.strategy.indicators import add_atr
from paper_signs_backend.app.strategy.sizing import calculate_shares

logger = logging.getLogger(__name__)


def get_trades(
    db: Session,
    symbol: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Trade]:
    """Return paginated trade history with optional filters."""
    q = db.query(Trade)
    if symbol:
        q = q.filter(Trade.symbol == symbol.upper().strip())
    if action:
        q = q.filter(Trade.action == action.upper().strip())
    return q.order_by(Trade.id.desc()).offset(offset).limit(limit).all()


def get_summary(db: Session) -> TradeSummary:
    """Return aggregate trade statistics."""
    rows = db.query(Trade).all()
    if not rows:
        return TradeSummary(
            total_trades=0,
            total_pnl=0.0,
            wins=0,
            losses=0,
            win_rate=0.0,
            profit_factor=0.0,
            avg_win=0.0,
            avg_loss=0.0,
        )

    # Exclude open/zero pnl buys for win rate calculation
    sell_trades = [t for t in rows if t.action == "SELL"]
    total_pnl = sum(t.pnl or 0 for t in sell_trades)
    
    win_trades = [t for t in sell_trades if (t.pnl or 0) > 0]
    loss_trades = [t for t in sell_trades if (t.pnl or 0) <= 0]
    
    wins = len(win_trades)
    losses = len(loss_trades)
    win_rate = round((wins / len(sell_trades) * 100), 1) if sell_trades else 0.0
    
    gross_profits = sum(t.pnl for t in win_trades if t.pnl)
    gross_losses = abs(sum(t.pnl for t in loss_trades if t.pnl))
    profit_factor = round(gross_profits / max(0.01, gross_losses), 2) if gross_losses > 0 else (gross_profits if gross_profits > 0 else 1.0)
    avg_win = round(gross_profits / wins, 2) if wins > 0 else 0.0
    avg_loss = round(gross_losses / losses, 2) if losses > 0 else 0.0

    return TradeSummary(
        total_trades=len(rows),
        total_pnl=round(total_pnl, 2),
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        profit_factor=profit_factor,
        avg_win=avg_win,
        avg_loss=avg_loss,
    )


def insert_trade(
    db: Session,
    *,
    trade_date: date,
    symbol: str,
    action: str,
    shares: int,
    price: float,
    cost: float,
    pnl: float = 0.0,
    broker_order_id: Optional[str] = None,
) -> Trade:
    """Persist a new trade record."""
    trade = Trade(
        trade_date=trade_date,
        symbol=symbol.upper().strip(),
        action=action.upper().strip(),
        shares=shares,
        price=price,
        cost=cost,
        pnl=pnl,
        broker_order_id=broker_order_id,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


def execute_trade(
    db: Session,
    symbol: str,
    action: str = "BUY",
    shares: Optional[int] = None,
    price: Optional[float] = None,
    notes: Optional[str] = None,
) -> ExecuteTradeResponse:
    """
    Execute a paper trade immediately via the broker and persist it to DB.
    """
    broker = get_broker()
    account = broker.get_account()
    clean_sym = symbol.upper().strip()
    clean_act = action.upper().strip()

    if clean_act == "BUY":
        # Determine shares if not specified
        if shares is None or shares <= 0:
            try:
                df = get_ohlcv(clean_sym, period="3mo")
                df_atr = add_atr(df)
                last_atr = float(df_atr["ATR20"].iloc[-1])
                last_close = float(df_atr["Close"].iloc[-1])
                calculated_shares, _ = calculate_shares(
                    equity=account.equity,
                    close=last_close,
                    atr=last_atr,
                    available_cash=account.cash,
                )
                shares = max(1, calculated_shares)
            except Exception:
                shares = 10

        res = broker.submit_buy(symbol=clean_sym, shares=shares, note=notes)
        if not res.success:
            return ExecuteTradeResponse(
                success=False,
                symbol=clean_sym,
                action="BUY",
                shares=shares,
                filled_price=0.0,
                cost=0.0,
                pnl=0.0,
                message=res.error or "Failed to execute BUY order",
            )

        insert_trade(
            db=db,
            trade_date=date.today(),
            symbol=clean_sym,
            action="BUY",
            shares=res.shares,
            price=res.filled_price,
            cost=res.cost,
            pnl=0.0,
            broker_order_id=res.order_id,
        )

        return ExecuteTradeResponse(
            success=True,
            symbol=clean_sym,
            action="BUY",
            shares=res.shares,
            filled_price=res.filled_price,
            cost=res.cost,
            pnl=0.0,
            message=f"Successfully executed BUY of {res.shares} {clean_sym} @ ${res.filled_price:.2f}",
            order_id=res.order_id,
        )

    elif clean_act == "SELL":
        # Find position
        pos = next((p for p in account.positions if p.symbol == clean_sym), None)
        sell_shares = shares if (shares and shares > 0) else (pos.shares if pos else 0)
        if sell_shares <= 0:
            return ExecuteTradeResponse(
                success=False,
                symbol=clean_sym,
                action="SELL",
                shares=0,
                filled_price=0.0,
                cost=0.0,
                pnl=0.0,
                message=f"No open position to sell for {clean_sym}",
            )

        avg_entry = pos.avg_entry_price if pos else 0.0
        res = broker.submit_sell(symbol=clean_sym, shares=sell_shares, note=notes)
        if not res.success:
            return ExecuteTradeResponse(
                success=False,
                symbol=clean_sym,
                action="SELL",
                shares=sell_shares,
                filled_price=0.0,
                cost=0.0,
                pnl=0.0,
                message=res.error or "Failed to execute SELL order",
            )

        pnl = (res.filled_price - avg_entry) * res.shares
        insert_trade(
            db=db,
            trade_date=date.today(),
            symbol=clean_sym,
            action="SELL",
            shares=res.shares,
            price=res.filled_price,
            cost=res.cost,
            pnl=round(pnl, 2),
            broker_order_id=res.order_id,
        )

        return ExecuteTradeResponse(
            success=True,
            symbol=clean_sym,
            action="SELL",
            shares=res.shares,
            filled_price=res.filled_price,
            cost=res.cost,
            pnl=round(pnl, 2),
            message=f"Successfully sold {res.shares} {clean_sym} @ ${res.filled_price:.2f} (PnL: ${pnl:+.2f})",
            order_id=res.order_id,
        )

    return ExecuteTradeResponse(
        success=False,
        symbol=clean_sym,
        action=clean_act,
        shares=0,
        filled_price=0.0,
        cost=0.0,
        pnl=0.0,
        message=f"Unknown action: {clean_act}",
    )