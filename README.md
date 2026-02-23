# Sensex 1‑Min Options Scalping Algo

Intraday scalping system for **ATM weekly Sensex options** on 1‑minute candles, with strict risk management, automated trade execution, and trade persistence.

### Features

- **Strategy**
  - 1‑min candles on Sensex spot.
  - Indicators: EMA9, EMA21, VWAP.
  - Pullback‑based entries (bullish for CE / bearish for PE).
- **Risk**
  - Max trades/day, max consecutive losses.
  - Daily loss limit (% of capital) with **automatic position flattening**.
  - Per‑trade risk based position sizing.
  - Liquidity validation before entry.
- **Execution**
  - ATM strike selection (rounded to nearest 100).
  - Target +12% / SL −8% on option premium.
  - Opposite‑signal exits (EMA cross reversal).
  - End‑of‑day forced exit — no overnight positions.
  - Graceful shutdown with position flattening.
- **Broker Integration**
  - `KiteClientStub` — backtest/simulation using CSV data.
  - `KiteClientLive` — real Kite (Zerodha) trading via BFO exchange.
  - `KiteClientPaper` — **paper trading** with real market data and simulated orders.
- **Persistence**
  - SQLite trade logging via `TradeLogger` — records all entries, exits, P&L, and exit reasons.

### Project Structure

- `main.py` – Entrypoint for backtest/stub loop.
- `paper_trade.py` – Entrypoint for paper trading (real data, simulated orders).
- `config.yaml` – All runtime configuration (account, risk, broker, windows).
- `core/`
  - `app.py` – Orchestration:
    - `main_stub_loop` – backtest/simulation runs.
    - `build_live_on_candle_handler` – live WebSocket‑driven trading.
    - `build_paper_trading_handler` / `run_paper_trading` – paper trading mode.
  - `config_loader.py` – YAML config loader with validation.
  - `logger.py` – Logging setup.
  - `utils.py`, `constants.py` – Shared helpers and constants.
- `strategy/`
  - `indicators.py` – EMA9, EMA21, VWAP over 1‑min candles.
  - `signal_engine.py` – Entry signal logic (CE/PE).
  - `strike_selector.py` – ATM strike selection from spot price.
- `risk/`
  - `risk_engine.py` – Trading windows, daily limits, loss limit breach detection.
  - `position_sizer.py` – Position size from risk % and SL%.
- `execution/`
  - `trade_manager.py` – Entry, exit, force‑exit, P&L + risk updates, liquidity checks.
  - `exit_engine.py` – Target/SL/opposite‑signal/EOD exit decisions.
- `broker/`
  - `kite_client.py` – `KiteClientStub`, `KiteClientLive`, `KiteClientPaper`.
  - `order_manager.py` – Thin wrapper around broker orders.
  - `websocket_handler.py` – Tick → 1‑min candle builder (minute‑boundary detection).
  - `kite_stream.py` – KiteTicker wiring to the websocket handler.
- `database/`
  - `models.py` – SQLAlchemy `Trade` model.
  - `db_manager.py` – `TradeLogger` for SQLite persistence.
- `tests/` – Unit tests for strategy, risk, orders, and risk‑breach scenarios.

### Setup

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure `config.yaml`**

   - Set `account.initial_capital`, `risk.*`, and `trade_params.*` as desired.
   - For live/paper trading with Kite:
     - Fill `broker.api_key` and `broker.access_token` (or use env vars).
     - Set `broker.ticker_tokens` to the Sensex instrument token for streaming.

3. **Environment variables** (recommended for credentials)

   ```bash
   export KITE_API_KEY="your_api_key"
   export KITE_ACCESS_TOKEN="your_access_token"
   ```

### Running

- **Backtest / Stub loop** (uses CSV data via `KiteClientStub`):

  ```bash
  python main.py
  ```

- **Paper trading** (real market data, simulated orders):

  ```bash
  python paper_trade.py
  ```

  Orders are logged with `[PAPER ORDER]` prefix. Trades are saved to `trades.db`.

- **Live trading** (real orders via Kite):

  ```python
  from core.app import build_live_on_candle_handler

  config, on_candle, ws_handler, ticker = build_live_on_candle_handler()
  ticker.connect()  # Blocks; pipeline runs on each 1‑min candle
  ```

### Tests

```bash
python -m pytest tests/ -v
```

> **⚠️ Warning:** Live trading involves real financial risk. Always paper trade first, verify option symbol formats against Kite's `instruments.csv`, and validate all logic before enabling real capital.
