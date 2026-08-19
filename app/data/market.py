"""Market data fetching via yfinance with caching and retry logic."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from paper_signs_backend.app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# In-memory cache: symbol → (timestamp, DataFrame)
_cache: Dict[str, tuple[float, pd.DataFrame]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


def _fetch_raw(symbol: str, period: str, retries: int = 3) -> pd.DataFrame:
    """Download OHLCV data from yfinance with retry."""
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            df = yf.download(
                symbol,
                period=period,
                interval="1d",
                auto_adjust=True,
                progress=False,
                actions=False,
            )
            if df.empty:
                raise ValueError(f"Empty response for {symbol}")
            # Flatten multi-index columns if present (yfinance >= 0.2.x)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)
            df.dropna(subset=["Close"], inplace=True)
            return df
        except Exception as exc:
            last_err = exc
            logger.warning(
                "yfinance attempt %d/%d failed for %s: %s",
                attempt,
                retries,
                symbol,
                exc,
            )
            if attempt < retries:
                time.sleep(2 ** attempt)  # exponential backoff
    raise RuntimeError(f"Failed to fetch {symbol} after {retries} attempts") from last_err


def get_ohlcv(
    symbol: str,
    period: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Return a cleaned OHLCV DataFrame for *symbol*.

    Uses an in-process TTL cache to avoid hammering Yahoo Finance.
    Pass force_refresh=True to bypass the cache.
    """
    cache_key = f"{symbol}:{period}:{start}:{end}"
    now = time.monotonic()

    if not force_refresh and cache_key in _cache:
        cached_at, cached_df = _cache[cache_key]
        if now - cached_at < CACHE_TTL_SECONDS:
            return cached_df.copy()

    effective_period = period or settings.data_period

    if start or end:
        # Date-range download overrides period
        df = _fetch_by_dates(symbol, start=start, end=end)
    else:
        df = _fetch_raw(symbol, period=effective_period)

    _cache[cache_key] = (now, df)
    return df.copy()


def _fetch_by_dates(
    symbol: str,
    start: Optional[str],
    end: Optional[str],
    retries: int = 3,
) -> pd.DataFrame:
    """Download OHLCV for a specific date range."""
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            df = yf.download(
                symbol,
                start=start,
                end=end,
                interval="1d",
                auto_adjust=True,
                progress=False,
                actions=False,
            )
            if df.empty:
                raise ValueError(f"Empty response for {symbol} [{start}:{end}]")
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)
            df.dropna(subset=["Close"], inplace=True)
            return df
        except Exception as exc:
            last_err = exc
            logger.warning("Date-range fetch attempt %d failed for %s: %s", attempt, symbol, exc)
            if attempt < retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed date-range fetch for {symbol}") from last_err


def get_all_symbols(
    symbols: Optional[List[str]] = None,
    period: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict[str, pd.DataFrame]:
    """
    Fetch OHLCV for all symbols. Returns only those that succeeded.
    Errors are logged and the symbol is skipped.
    """
    target_symbols = symbols or settings.symbol_list
    results: Dict[str, pd.DataFrame] = {}
    for sym in target_symbols:
        try:
            df = get_ohlcv(sym, period=period, start=start, end=end, force_refresh=force_refresh)
            results[sym] = df
            logger.debug("Fetched %d rows for %s", len(df), sym)
        except Exception as exc:
            logger.error("Skipping %s — %s", sym, exc)
    return results


def clear_cache() -> None:
    """Flush the in-process data cache."""
    _cache.clear()
