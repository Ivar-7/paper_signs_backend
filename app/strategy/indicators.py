"""
Technical indicators          pure pandas/numpy, no side effects.

All functions accept a DataFrame with OHLCV columns and return
a new DataFrame with additional indicator columns appended.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from paper_signs_backend.app.strategy.constants import (
    ATR_LENGTH,
    ENTRY_LOOKBACK,
    EXIT_LOOKBACK,
    SMA_LENGTH,
)


def add_sma(df: pd.DataFrame, length: int = SMA_LENGTH, source: str = "Close") -> pd.DataFrame:
    """Add a simple moving average column."""
    df = df.copy()
    col = f"SMA{length}"
    df[col] = df[source].rolling(window=length, min_periods=length).mean()
    return df


def add_atr(df: pd.DataFrame, length: int = ATR_LENGTH) -> pd.DataFrame:
    """
    Add Average True Range column (Wilder / simple rolling mean variant).
    ATR is used for position sizing          NOT as a stop trigger.
    """
    df = df.copy()
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df[f"ATR{length}"] = tr.rolling(window=length, min_periods=length).mean()
    return df


def add_donchian_entry_high(
    df: pd.DataFrame,
    lookback: int = ENTRY_LOOKBACK,
    source: str = "High",
) -> pd.DataFrame:
    """
    Add the entry breakout level: the highest High of the previous *lookback*
    completed bars (excludes today bar via shift(1)).

    Entry condition: Close[t] > EntryHigh[t]
    """
    df = df.copy()
    df["EntryHigh"] = (
        df[source]
        .rolling(window=lookback, min_periods=lookback)
        .max()
        .shift(1)
    )
    return df


def add_donchian_exit_low(
    df: pd.DataFrame,
    lookback: int = EXIT_LOOKBACK,
    source: str = "Low",
) -> pd.DataFrame:
    """
    Add the exit breakdown level: the lowest Low of the previous *lookback*
    completed bars (excludes today bar via shift(1)).

    Exit condition: Close[t] < ExitLow[t]
    """
    df = df.copy()
    df["ExitLow"] = (
        df[source]
        .rolling(window=lookback, min_periods=lookback)
        .min()
        .shift(1)
    )
    return df


def add_all_indicators(
    df: pd.DataFrame,
    sma_length: int = SMA_LENGTH,
    entry_lookback: int = ENTRY_LOOKBACK,
    exit_lookback: int = EXIT_LOOKBACK,
    atr_length: int = ATR_LENGTH,
) -> pd.DataFrame:
    """Apply all strategy indicators in one call."""
    df = add_sma(df, length=sma_length)
    df = add_atr(df, length=atr_length)
    df = add_donchian_entry_high(df, lookback=entry_lookback)
    df = add_donchian_exit_low(df, lookback=exit_lookback)
    return df
