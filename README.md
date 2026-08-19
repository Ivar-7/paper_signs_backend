# TrendBot — Automated Donchian Trend Strategy

**100/50 Donchian Channel + SMA200 regime filter + ATR(20) position sizing**  
Fully automated paper trading bot with a premium web dashboard. 100% free — no subscriptions, no paid APIs.

---

## Strategy Rules (DO NOT MODIFY after first backtest)

| Parameter | Value |
|---|---|
| Entry | Close > 100-day High (shifted) AND > SMA200 |
| Exit | Close < 50-day Low OR < SMA200 |
| Timeframe | Daily (signal on close, fill on next open) |
| Risk per trade | 0.5% of equity |
| ATR sizing | 2 × ATR(20) stop distance |
| Max position | 25% of equity |
| Max positions | 4 simultaneous |
| Leverage | None (1×) |

## Instruments

`SPY QQQ IWM EFA EEM TLT GLD DBC VNQ UUP`

---

## Quick Start

### 1. Install Python 3.11+

### 2. Create virtual environment
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
copy .env.example .env   # Windows
cp .env.example .env     # macOS/Linux
# Edit .env if needed (default is internal paper sim, no API key required)
```

### 5. Run the server
```bash
python run.py
```

Open **http://localhost:8000** in your browser.

---

## First-Time Setup

### Run the backtest
Click **🧪 Run Backtest (All Periods)** on the Backtest tab.  
This downloads ~15 years of data and runs three test periods. Allow 2–5 minutes.

### Run today's signals
Click **▶ Run Now** in the header.  
The bot will fetch today's data, compute signals, and update the dashboard.

### Automated daily execution
The scheduler runs automatically at **22:30 UTC** on weekdays (configurable via `SCHEDULE_CRON` in `.env`).

---

## Using Alpaca Paper Trading (Optional)

1. Sign up free at [alpaca.markets](https://alpaca.markets)
2. Go to Paper Trading → API Keys → Generate
3. In `.env`:
   ```
   BROKER=alpaca
   ALPACA_API_KEY=your_key_here
   ALPACA_SECRET_KEY=your_secret_here
   ```
4. Restart the server

---

## Project Structure

```
paper_signs/
├── backend/
│   └── app/
│       ├── config.py         # All settings (pydantic-settings)
│       ├── main.py           # FastAPI app + scheduler
│       ├── scheduler.py      # Daily run logic
│       ├── strategy/
│       │   ├── indicators.py # SMA, ATR, Donchian
│       │   ├── signals.py    # Entry/exit logic
│       │   └── sizing.py     # ATR position sizing
│       ├── data/
│       │   ├── market.py     # yfinance with caching
│       │   └── store.py      # DB read/write helpers
│       ├── broker/
│       │   ├── base.py       # Abstract interface
│       │   ├── paper.py      # Internal simulation
│       │   └── alpaca.py     # Alpaca paper API
│       ├── backtest/
│       │   ├── engine.py     # Vectorized backtest
│       │   └── metrics.py    # CAGR, Sharpe, Sortino, etc.
│       ├── models/db.py      # SQLAlchemy ORM
│       └── api/              # FastAPI routers
├── frontend/
│   ├── index.html            # Premium dashboard
│   ├── css/style.css
│   └── js/
│       ├── api.js            # API client
│       ├── signals.js        # Signal card rendering
│       ├── charts.js         # Chart.js wrappers
│       └── dashboard.js      # Main controller
├── .env                      # Your config (git-ignored)
├── .env.example              # Template
├── requirements.txt
└── run.py
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/signals/` | Today's signals |
| GET | `/api/portfolio/` | Live portfolio |
| GET | `/api/portfolio/history` | Equity curve |
| GET | `/api/trades/` | Trade history |
| POST | `/api/backtest/run?period=all` | Run backtest |
| GET | `/api/backtest/results` | Backtest metrics |
| POST | `/api/backtest/robustness` | Robustness tests |
| POST | `/api/run` | Manual strategy run |
| GET | `/api/status` | System status |

Full interactive docs: **http://localhost:8000/docs**

---

## Testing Stages

| Stage | Period | Purpose |
|---|---|---|
| Dev | 2010–2019 | Find bugs, establish strategy |
| Validation | 2020–2023 | Freeze parameters, check robustness |
| OOS | 2024–present | Genuinely unseen data |
| Live Paper | Aug 19, 2026 → | Real-time forward test |

**Never modify strategy parameters based on OOS or live results.**

---

## Robustness Tests

Run via **🔬 Run Robustness Tests** on the Backtest tab.

1. **Parameter perturbation** — Grid of Entry (80–120) × SMA (150–250) variations
2. **Market removal** — Remove one ETF at a time, rerun
3. **Cost stress** — Test at 0%, 0.05%, 0.10%, 0.20% commission

A robust strategy should show a flat heatmap plateau, not a single lucky parameter spike.

---

## Windows Task Scheduler (auto-run daily)

1. Open **Task Scheduler**
2. Create Basic Task
3. Trigger: Daily, repeat on weekdays
4. Time: 11:00 PM (23:00) local time (adjust for your timezone vs UTC)
5. Action: Start a program
   - Program: `C:\path\to\paper_signs\.venv\Scripts\python.exe`
   - Argument: `C:\path\to\paper_signs\run.py`
   - Start in: `C:\path\to\paper_signs`

Or just leave the web server running — the built-in APScheduler handles it automatically.

---

## Important Notes

- **No look-ahead bias**: Signals use close[t], fills use open[t+1]
- **No leverage**: Purely long-only, 1× capital
- **No optimization**: Do not change parameters after seeing backtest results
- **Free data**: Yahoo Finance via yfinance (15 years history)
- **Free broker**: Internal paper simulation or Alpaca paper account
