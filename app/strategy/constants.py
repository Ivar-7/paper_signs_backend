"""
Strategy algorithm constants          fixed values that define the trading logic.

These are NOT environment variables. They are algorithm parameters that should
only change after deliberate research and backtesting. Do not move these to .env.
"""

# Donchian channel lookbacks
ENTRY_LOOKBACK: int = 100   # bars to look back for entry breakout high
EXIT_LOOKBACK: int = 50     # bars to look back for exit breakdown low

# Trend filter
SMA_LENGTH: int = 200       # simple moving average period

# Volatility / position sizing
ATR_LENGTH: int = 20        # ATR period for position sizing
ATR_MULTIPLIER: float = 2.0 # ATR multiplier for stop distance calculation

# Risk parameters
RISK_PER_TRADE: float = 0.005   # fraction of equity risked per trade (0.5%)
MAX_POSITIONS: int = 4           # maximum concurrent open positions
MAX_POSITION_PCT: float = 0.25   # maximum fraction of equity in one position (25%)
INITIAL_CAPITAL: float = 100_000.0  # starting capital for backtests

# Backtest periods (name -> (start_date, end_date); None end = today)
BACKTEST_PERIODS: dict = {
    "dev":        ("2010-01-01", "2019-12-31"),
    "validation": ("2020-01-01", "2023-12-31"),
    "oos":        ("2024-01-01", None),
}
