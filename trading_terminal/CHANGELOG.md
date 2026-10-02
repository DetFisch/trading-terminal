# Changelog

## 0.1.5 - 2026-10-02
- **Connect Claude** (Assistant): sign in with your Claude subscription the same way the Claude Code CLI does. Ask AI, the morning brief and headline sentiment then run on your subscription. New `ai_choice` setting (auto = subscription, then Anthropic API key, then Gemini).
- **My trading plan** (Assistant): goals, risk limits and rules, sent with every AI question along with your track record and recent journal notes.
- **Journal** (Home): every order you send is logged with your note and tags; add a review afterwards; win rate and profit/loss by setup tag.
- **Gains & dividends** (Home): realized gains (oldest shares first, short- vs long-term), dividends received and upcoming, CSV downloads.
- **Saved watchlists**: several named lists; add, remove and reorder them, or use "+ Watchlist" on any stock.
- **Size by risk** on the order card: shares worked out from how much you'll risk and your stop.
- **Headline sentiment**: each headline tagged Positive / Negative / Neutral, with an overall mood.
- **ForecastEx odds** on Predictions, read through IB Gateway (product codes set on that screen; FF to start).
- IBKR orders: the app waits a few seconds for IBKR to accept an order and shows IBKR's reason when it holds or rejects one.
- Claude Code is now installed in the add-on (first update takes longer).

## 0.1.4 - 2026-10-02
- Portfolio is the home screen; new **Home** section (Portfolio, Trade, Alerts). Clicking the logo goes home.
- Burnt-orange accent colour; gains stay green and losses are a true red.
- Order statuses in plain English ("Sending to IBKR", "Working", "Filled"...); the order list refreshes every 3 seconds; orders still being sent can be canceled.

## 0.1.3 - 2026-10-02
- The Interactive Brokers port now follows `trading_mode` when `ibkr_port` is left empty (4004 paper, 4003 live).

## 0.1.2 - 2026-10-02
- Default IB Gateway host corrected to `e8950327-ib-gateway` (add-ons installed from GitHub aren't named `local-...`).

## 0.1.1 - 2026-10-02
- Fixed the build failing with "pip: not found" (Home Assistant was swapping in its own base image).

## 0.1.0 - 2026-10-02
- First release as a Home Assistant add-on.
