# Trading Terminal: handoff

A personal, Bloomberg-style trading terminal with a Robinhood-like look. It's a single Streamlit app that
runs as a Home Assistant OS add-on on a Home Assistant Green (aarch64) and opens from the HA sidebar.
It trades through **Alpaca** and **Interactive Brokers** (paper by default). An AI research desk
(Claude through a Claude subscription, an Anthropic API key, or Gemini) answers questions using 30
read-only research tools. None of the AI tools can place, change or cancel orders.

## Where things live

| What | Where |
|---|---|
| Source (dev laptop) | `C:\AntiGravity\TradingApp` |
| GitHub (public, HA installs from here) | https://github.com/j0eyoung/trading-terminal |
| Add-ons | `trading_terminal/` (the app), `ib_gateway/` (IBKR's IB Gateway) |
| Keys and passwords | Only in each add-on's **Configuration** tab in Home Assistant. Locally in `.env`, which is never committed |
| Collected data | Your own storage (Backblaze B2 bucket, S3-compatible). Nothing large is kept on the Green |

The dev laptop is a work computer. That's why the code goes through GitHub and keys stay in HA.

## Architecture

- **`app.py`**: the whole UI. A function-code menu like Bloomberg's:
  - Home: PORT portfolio (home screen), ORD trade, JRNL journal, GAIN gains & dividends, ALRT alerts
  - Stock: DES, GP chart, N news, FA financials, VAL, ANR analysts, ERN earnings, SEC filings, OMON options, BT backtest
  - Market: MON, SPX S&P 500, IDEA ideas, CAL calendar, PRED prediction markets, SCR screener, ECO economy
  - Assistant: BRF morning brief, AI Ask AI, PLAN trading plan, CLD Connect Claude, DATA data collection, HELP
  - URL parameters: `?t=SYMBOL`, `?f=CODE`. Anything slower than 1 s is logged as `[speed] … took N s`.
- **`terminal/`**: the logic.
  - `config.py`: settings and keys from the environment
  - `brokers/`: `alpaca_broker.py` and `ibkr_broker.py` (ib_async), with a shared `base.py` (OrderRequest, brackets, activity)
  - `data.py`, `market.py`, `sources.py`: market data. Alpaca bars, news and options; Finnhub; FMP; FRED; SEC EDGAR (XBRL statements, about 15 years); Yahoo as a fallback
  - `stream.py`: the live Alpaca IEX websocket. The free plan allows one connection, and its state lives on the thread so it survives Streamlit reloads
  - `cache.py`: disk cache with background refresh (`get`, `latest`)
  - `store.py`, `collector.py`: data collection to S3-compatible storage or a folder (Parquet). Runs after 16:35 ET on weekdays
  - `ai.py`: picks the AI provider, holds the system prompt, streams answers
  - `claude_code.py`: drives the `claude` CLI headless, plus subscription sign-in
  - `tools.py`: the 30 read-only research tools
  - `sentiment.py`: headline sentiment
  - Others: `watchlists`, `journal`, `profile` (trading plan), `gains` (FIFO), `alerts`, `ideas`, `indicators`, `backtest`, `predictions` (Kalshi, Polymarket, ForecastEx)
- **`mcp_server.py`**: exposes `tools.TOOLS` over MCP. In the add-on it runs all the time at
  `http://127.0.0.1:8765` (`TERMINAL_MCP_URL`). Without that variable, Claude Code starts it over stdio.

### How Ask AI works with a Claude subscription

1. `ai.provider()` reads the `ai_choice` setting. `auto` tries Claude Code (signed in), then `ANTHROPIC_API_KEY`, then Gemini.
2. For Claude Code, the app sends a small context (screen, ticker, quote, holdings, plan) and runs:
   `claude -p --restricted --no-session-persistence --tools WebSearch WebFetch --effort high --strict-mcp-config --mcp-config <mcp.json> --allowedTools WebSearch WebFetch mcp__terminal --output-format stream-json`
3. Claude calls the `mcp__terminal__*` tools, and the UI shows "Looking up: …" while it does.
4. A 10-minute watchdog kills a hung run. Stderr is read continuously, and every step is logged as `[claude] …` in the add-on's Log tab.
5. If the CLI says the sign-in is expired or invalid, the app marks Claude as signed out. Ask AI then tells you to sign in again under **Assistant > Connect Claude**.

Effort: Ask AI and the morning brief run at high. Headline sentiment runs at low.

## Add-ons

| Add-on | Version | Notes |
|---|---|---|
| Trading Terminal | 0.1.16 | `python:3.12-slim-bookworm`, with Claude Code installed. `CLAUDE_CONFIG_DIR=/data/claude` keeps the sign-in across updates. `addon_entry.py` turns the HA options into environment variables, starts the MCP server and then Streamlit |
| IB Gateway | 0.1.3 | Wraps `ghcr.io/gnzsnz/ib-gateway:stable`. Paper is port 4004 and live is 4003. Its hostname for the app is `e8950327-ib-gateway`. Time zone America/Denver |

Main Trading Terminal settings:
- `trading_mode` (paper/live), `ai_choice`
- Alpaca paper and live keys; Gemini, Anthropic, Finnhub, FMP and FRED keys; `sec_contact_email`
- `watchlist`
- `ibkr_enabled`, `ibkr_host`, `ibkr_port` (empty means it follows the mode), `ibkr_client_id`
- `store_type` (off/s3/folder), `store_path`, `s3_endpoint`, `s3_bucket`, `s3_access_key`, `s3_secret_key`, `s3_prefix`, `s3_region`, `minute_backfill_days`

Known gotchas:
- The Supervisor ignores `build.yaml`, so the base image is hard-coded in the Dockerfile.
- Backblaze B2 needs boto3's checksum options set to `when_required`. This is already done in `store.py`.

## Release process (every push)

1. Make the change in the root files (`app.py`, `terminal/`, `mcp_server.py`, `requirements.txt`).
2. `powershell -File make_addon.ps1` copies the code into `trading_terminal/app`.
3. Raise `version:` in each changed add-on's `config.yaml`. That's what makes HA offer the update.
4. Add a dated entry at the top of that add-on's `CHANGELOG.md`. HA shows it in the update dialog.
5. `python -m pyflakes app.py mcp_server.py terminal`
6. Secret check: make sure no keys are in the diff and `.env` isn't staged.
7. Commit and push to `main`. Commits use the GitHub noreply email set in the repo's local git config.
8. In HA: Settings > Add-ons > Trading Terminal > Update.

## Testing locally

- `.claude/launch.json` has `terminal` (port 8501, real `.env`) and `terminal-ui-test` (port 8503, dummy
  Alpaca keys so it doesn't take the one live-stream connection from the Green).
- Headless test: `streamlit.testing.v1.AppTest` with `AI_CHOICE=claude_code` exercises Ask AI.
- Trades only on paper. Test orders have been $1 limits that never fill, cancelled afterwards.

## Known issues / next ideas

- The work network blocks Kalshi, Polymarket and IBKR's servers. Test those on the Green, not on the laptop.
- The Claude subscription sign-in can expire. Sign in again under Assistant > Connect Claude.
- The collector starts the first time the app is opened after the add-on starts.
- Ideas raised but not built yet: run the collector without opening the app, a journal coach, DCA and grid backtests, and maybe a home NAS as the storage target instead of B2.
