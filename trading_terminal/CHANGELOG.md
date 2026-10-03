# Changelog

## 0.1.10 - 2026-10-02
- **Financials** now come from companies' own SEC filings: about 15 years of annual results (Yahoo had 4) and 12 quarters, with a chart of the headline lines (revenue and net income, assets and liabilities, operating and free cash flow). Yahoo is still used for companies that don't file with the SEC.
- **Backtest** has a new "Max" period that tests a rule on a stock's entire price history (back to 1980 for Apple), so it's tested through the 2000 and 2008 crashes too.

## 0.1.9 - 2026-10-02
Data from official free APIs instead of Yahoo, with Yahoo kept as a backup:
- Price charts, mini charts and the S&P 500 scan now come from Alpaca's market data (your existing keys). The S&P 500 scan takes about 10 seconds instead of about a minute. Today's chart adds the last 15 minutes from the live feed, since the free full-market data runs 15 minutes behind. The "MAX" chart range still uses Yahoo (Alpaca goes back about 10 years).
- News comes from Alpaca's feed (Benzinga) first.
- Company profile, key statistics and analyst ratings come from Finnhub first, so a stock you haven't opened before shows its numbers in about a second; Yahoo's fuller profile (the description, employees, price targets) fills in from the background.
- New "Research elsewhere" links on every stock page: Stock Analysis, Seeking Alpha, Google Finance, Finviz, TradingView, plus Koyfin and TIKR.

## 0.1.8 - 2026-10-02
Faster clicks:
- Live sections redraw less often, so clicks don't queue behind them: price header every 3 s (was 1 s), watchlist every 5 s (was 2 s), market panel every 15 s (was 5 s), alerts every 30 s.
- Watchlist quotes, mini charts and the earnings-reminder dates show the last saved copy instantly and refresh in the background, instead of making a page wait while they reload.
- Speed log: anything taking over a second is written to this add-on's Log tab as `[speed] ... took N s`, to pin down what's slow.

## 0.1.7 - 2026-10-02
- Fixed: the section bar (Home, Stock, Market, Assistant) and screen buttons at the top were invisible in 0.1.6, so you couldn't move between screens.

## 0.1.6 - 2026-10-02
Faster screens:
- Clicking a stock in a watchlist, the market panel, your positions or the S&P 500 movers opens it in place instead of reloading the whole app.
- A new stock's quote, company info, news, chart and analyst data now load at the same time instead of one after another.
- Headline sentiment is worked out in the background: the news shows straight away and the tags appear a few seconds later.
- Account balances and positions are reused for 10 seconds instead of being fetched again on every click (refreshed right after you place an order).
- If IB Gateway is down, screens no longer wait up to 8 seconds per click for it; the app retries every 30 seconds.

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
