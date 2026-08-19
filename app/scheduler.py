"""
Daily strategy runner    '                                   called by APScheduler and manually via API.

Sequence:
  1. Fetch latest market data for all symbols
  2. Compute indicators
  3. Generate signals (store to DB)
  4. Process exits via broker
  5. Process entries via broker
  6. Snapshot portfolio to DB
  7. Log scheduler run
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Optional

from paper_signs_backend.app.broker import get_broker
from paper_signs_backend.app.config import get_settings
from paper_signs_backend.app.data.market import get_all_symbols, clear_cache

from paper_signs_backend.app.models.database import SessionLocal
from paper_signs_backend.app.strategy.constants import MAX_POSITIONS
from paper_signs_backend.app.strategy.signals import generate_all_signals
from paper_signs_backend.app.strategy.sizing import calculate_shares
from paper_signs_backend.app.modules.portfolio import service as portfolio_svc
from paper_signs_backend.app.modules.signals import service as signals_svc
from paper_signs_backend.app.modules.trades import service as trades_svc
from paper_signs_backend.app.models.orm import SchedulerRun

logger = logging.getLogger(__name__)
settings = get_settings()


def run_daily_strategy(triggered_by: str = "scheduler") -> dict:
    """
    Execute one full daily strategy cycle.

    Returns a summary dict for API responses.
    """
    start_ts = time.monotonic()
    today = date.today()
    trades_executed = 0
    errors: list[str] = []

    logger.info("=== Daily strategy run started [%s] ===", triggered_by)
    clear_cache()  # Force fresh data

    db = SessionLocal()
    broker = get_broker()

    try:
        #    '                                     '                                   1. Fetch market data    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
        logger.info("Fetching market data for %s", settings.symbol_list)
        market_data = get_all_symbols(force_refresh=True)
        if not market_data:
            raise RuntimeError("No market data returned from yfinance")

        #    '                                     '                                   2. Get current account state    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
        account = broker.get_account()
        held_symbols = [p.symbol for p in account.positions]
        open_count = len(held_symbols)
        logger.info(
            "Account: equity=$%.2f  cash=$%.2f  positions=%d",
            account.equity,
            account.cash,
            open_count,
        )

        #    '                                     '                                   3. Generate signals    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
        signals = generate_all_signals(
            market_data=market_data,
            current_equity=account.equity,
            held_symbols=held_symbols,
            open_position_count=open_count,
        )

        # Persist signals to DB
        for sig in signals:
            try:
                signals_svc.upsert_signal(
                    db=db,
                    signal_date=today,
                    symbol=sig.symbol,
                    close=sig.close,
                    entry_high=sig.entry_high,
                    exit_low=sig.exit_low,
                    sma200=sig.sma200,
                    atr20=sig.atr20,
                    entry_signal=sig.entry_signal,
                    exit_signal=sig.exit_signal,
                    suggested_shares=sig.suggested_shares,
                    suggested_cost=sig.suggested_cost,
                )
            except Exception as exc:
                logger.error("Failed to persist signal for %s: %s", sig.symbol, exc)

        #    '                                     '                                   4. Process exits    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
        exit_signals = [s for s in signals if s.exit_signal]
        for sig in exit_signals:
            position = next((p for p in account.positions if p.symbol == sig.symbol), None)
            if not position:
                continue

            logger.info("EXIT signal for %s (exit_reason: %s)", sig.symbol, sig.exit_reason)
            result = broker.submit_sell(symbol=sig.symbol, shares=position.shares)

            if result.success:
                pnl = (result.filled_price - position.avg_entry_price) * result.shares
                trades_svc.insert_trade(
                    db=db,
                    trade_date=today,
                    symbol=sig.symbol,
                    action="SELL",
                    shares=result.shares,
                    price=result.filled_price,
                    cost=result.cost,
                    pnl=round(pnl, 2),
                    broker_order_id=result.order_id,
                )
                trades_executed += 1
                logger.info(
                    "SOLD %s: %d shares @ %.4f  PnL=%.2f",
                    sig.symbol,
                    result.shares,
                    result.filled_price,
                    pnl,
                )
            else:
                errors.append(f"SELL {sig.symbol}: {result.error}")
                logger.error("SELL failed for %s: %s", sig.symbol, result.error)

        #    '                                     '                                   5. Refresh account after exits    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
        account = broker.get_account()
        held_symbols = [p.symbol for p in account.positions]
        open_count = len(held_symbols)

        #    '                                     '                                   6. Process entries    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
        entry_signals = [
            s for s in signals
            if s.entry_signal
            and s.symbol not in held_symbols
            and s.suggested_shares
            and s.suggested_shares > 0
        ]

        for sig in entry_signals:
            if open_count >= MAX_POSITIONS:
                break

            logger.info("ENTRY signal for %s (reason: %s)", sig.symbol, sig.entry_reason)

            # Re-calculate shares with current account cash
            shares, cost = calculate_shares(
                equity=account.equity,
                close=sig.close,
                atr=sig.atr20,
                available_cash=account.cash,
            )
            if shares <= 0:
                logger.warning("Skipping %s    '                                   insufficient cash", sig.symbol)
                continue

            result = broker.submit_buy(symbol=sig.symbol, shares=shares)
            if result.success:
                trades_svc.insert_trade(
                    db=db,
                    trade_date=today,
                    symbol=sig.symbol,
                    action="BUY",
                    shares=result.shares,
                    price=result.filled_price,
                    cost=result.cost,
                    pnl=0.0,
                    broker_order_id=result.order_id,
                )
                trades_executed += 1
                open_count += 1
                # Reduce available cash estimate
                account = broker.get_account()
                logger.info(
                    "BOUGHT %s: %d shares @ %.4f  cost=%.2f",
                    sig.symbol,
                    result.shares,
                    result.filled_price,
                    result.cost,
                )
            else:
                errors.append(f"BUY {sig.symbol}: {result.error}")
                logger.error("BUY failed for %s: %s", sig.symbol, result.error)

        #    '                                     '                                   7. Snapshot portfolio    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
        final_account = broker.get_account()
        positions_dict = {
            p.symbol: {
                "shares": p.shares,
                "avg_entry_price": p.avg_entry_price,
                "current_price": p.current_price,
                "unrealized_pnl": p.unrealized_pnl,
                "entry_date": p.entry_date,
            }
            for p in final_account.positions
        }
        portfolio_svc.upsert_snapshot(
            db=db,
            snapshot_date=today,
            equity=final_account.equity,
            cash=final_account.cash,
            positions=positions_dict,
        )

        #    '                                     '                                   8. Log run    '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                     '                                  
        duration = time.monotonic() - start_ts
        status = "error" if errors else "success"
        msg = "; ".join(errors) if errors else f"OK    '                                   {trades_executed} trade(s)"
        _insert_scheduler_run(
            db=db,
            run_date=today,
            status=status,
            message=msg,
            duration_seconds=round(duration, 2),
            trades_executed=trades_executed,
        )

        logger.info(
            "=== Daily run complete in %.1fs: %d trades, %d errors ===",
            duration,
            trades_executed,
            len(errors),
        )

        return {
            "status": status,
            "run_date": today.isoformat(),
            "trades_executed": trades_executed,
            "equity": final_account.equity,
            "cash": final_account.cash,
            "open_positions": len(final_account.positions),
            "signals_generated": len(signals),
            "errors": errors,
            "duration_seconds": round(duration, 2),
        }

    except Exception as exc:
        duration = time.monotonic() - start_ts
        logger.exception("Daily strategy run failed: %s", exc)
        _insert_scheduler_run(
            db=db,
            run_date=today,
            status="error",
            message=str(exc),
            duration_seconds=round(duration, 2),
            trades_executed=trades_executed,
        )
        return {
            "status": "error",
            "run_date": today.isoformat(),
            "trades_executed": trades_executed,
            "error": str(exc),
        }
    finally:
        db.close()


def _insert_scheduler_run(
    db,
    run_date,
    status: str,
    message=None,
    duration_seconds=None,
    trades_executed=None,
) -> None:
    """Persist a scheduler run log entry."""
    run = SchedulerRun(
        run_date=run_date,
        status=status,
        message=message,
        duration_seconds=duration_seconds,
        trades_executed=trades_executed,
    )
    db.add(run)
    db.commit()
