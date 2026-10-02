"""Trading terminal. Run with:  .venv\\Scripts\\streamlit run app.py"""
from __future__ import annotations

import hashlib
import html as htmllib
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from terminal import alerts, backtest, cache, config, data, ideas, predictions, sources, stream
from terminal import indicators as ind
from terminal.brokers import OrderRequest, connect_all

# Sections and their screens. The codes also work typed into the search box ("NVDA GP").
NAV = {
    "Home": {"PORT": "Portfolio", "ORD": "Trade", "ALRT": "Alerts"},
    "Stock": {"DES": "Overview", "GP": "Chart", "N": "News", "FA": "Financials", "VAL": "Valuation",
              "ANR": "Analysts", "ERN": "Earnings", "SEC": "Filings & insiders", "OMON": "Options",
              "BT": "Backtest"},
    "Market": {"MON": "Watchlist", "SPX": "S&P 500", "IDEA": "Ideas", "CAL": "Earnings calendar",
               "PRED": "Predictions", "SCR": "Screens", "ECO": "Economy"},
    "Assistant": {"BRF": "Morning brief", "AI": "Ask AI", "HELP": "Shortcuts"},
}
HOME = "PORT"  # first screen, like Robinhood's home: account value, positions, watchlist
FUNCTIONS = {code: label for items in NAV.values() for code, label in items.items()}
GROUP_OF = {code: group for group, items in NAV.items() for code in items}
# Brand accent is burnt orange; green and red are kept only for gains and losses, and the loss red
# is a true red so it is never mistaken for the accent.
ORANGE = "#e2711d"
AMBER, GREEN, RED, MUTED = "#f5a524", "#00c805", "#f6465d", "#8c8c8c"
CLEAR = "rgba(0,0,0,0)"
LINE = "#1e2124"  # hairline borders and chart grid

st.set_page_config(page_title="Terminal", page_icon="▮", layout="wide")
CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .stApp, button, input, textarea, select, p, li, td, th {font-family: 'Inter', sans-serif !important;}
header[data-testid="stHeader"] {display: none;}
/* Live sections redraw every second or two; don't dim them while they do */
[data-stale="true"] {opacity: 1 !important; transition: none !important;}
.block-container {padding: .9rem 2.2rem 2rem; max-width: 1480px;}
h3 {font-size: 1.35rem !important; font-weight: 700 !important; padding: 1.4rem 0 .5rem !important;
    border-bottom: 1px solid #1e2124; margin-bottom: .6rem !important;}
hr {border-color: #1e2124 !important; margin: .4rem 0 1rem !important;}
[data-testid="stMetricValue"] {font-size: 1.5rem; font-weight: 700; font-variant-numeric: tabular-nums;}
[data-testid="stMetricLabel"] {color: #8c8c8c;}

/* Tabs: section bar, range selectors, buy/sell -- plain text, active one underlined in the accent */
[data-testid="stButtonGroup"] button[data-variant="segmented_control"] {
    background: transparent !important; border: none !important; box-shadow: none !important;
    border-radius: 0 !important; padding: .3rem .1rem !important; margin-right: 1.15rem; color: #fff !important;
    font-weight: 600; border-bottom: 2px solid transparent !important;}
[data-testid="stButtonGroup"] button[data-variant="segmented_control"]:hover {color: var(--acc) !important;}
[data-testid="stButtonGroup"] button[data-variant="segmented_control"][aria-checked="true"] {
    color: var(--acc) !important; border-bottom: 2px solid var(--acc) !important;}
/* Chips: the screen picker under the top bar */
[data-testid="stButtonGroup"] button[data-variant="pills"] {
    background: #1e2124 !important; border: none !important; color: #fff !important; font-weight: 600;
    border-radius: 999px !important; padding: .25rem .9rem !important;}
[data-testid="stButtonGroup"] button[data-variant="pills"]:hover {background: #2a2d31 !important;}
[data-testid="stButtonGroup"] button[data-variant="pills"][aria-checked="true"],
[data-testid="stButtonGroup"] button[data-variant="pills"][aria-pressed="true"],
[data-testid="stButtonGroup"] button[data-variant="pills"][data-selected="true"] {
    background: var(--acc) !important; color: #000 !important;}
/* Buttons: accent pill for the main action, outlined pill otherwise */
[data-testid="stBaseButton-primary"] {background: var(--acc) !important; color: #000 !important; border: none !important;
    border-radius: 999px !important; font-weight: 700 !important; min-height: 2.9rem;}
[data-testid="stBaseButton-primary"]:hover {filter: brightness(1.12);}
[data-testid="stBaseButton-primary"] * {color: #000 !important;}
[data-testid="stBaseButton-primary"]:disabled {opacity: .45;}
[data-testid="stButtonGroup"] button[data-variant="pills"][aria-checked="true"] * {color: #000 !important;}
[data-testid="stBaseButton-secondary"] {background: transparent !important; color: var(--acc) !important;
    border: 1px solid var(--acc) !important; border-radius: 999px !important; font-weight: 600 !important;}
[data-testid="stTextInputRootElement"], [data-baseweb="select"] > div, [data-testid="stNumberInputContainer"] {
    border-radius: .5rem !important;}
[data-testid="stTextInputRootElement"]:has(input[aria-label="Search"]) {border-radius: 999px !important; background: #1e2124 !important;}
[data-testid="stExpander"] details {border: none !important; border-top: 1px solid #1e2124 !important; border-radius: 0 !important;}

.brand {font-weight: 800; font-size: 1.15rem; color: var(--acc); letter-spacing: -.01em; white-space: nowrap;}
.mode {text-align: right;}
.mode span {font-size: .72rem; font-weight: 700; padding: .25rem .6rem; border-radius: 999px; letter-spacing: .04em;}

/* Stock header */
.tk-name {font-size: 2.1rem; font-weight: 600; line-height: 1.15;}
.tk-px {font-size: 2.1rem; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1.2;}
.tk-chg {font-weight: 600; font-variant-numeric: tabular-nums; margin-top: .15rem;}
.tk-chg small {color: #8c8c8c; font-weight: 500; margin-left: .3rem;}
.tk-sub {color: #8c8c8c; font-size: .8rem; margin-top: .35rem; font-variant-numeric: tabular-nums;}
.dot {display: inline-block; width: .5rem; height: .5rem; border-radius: 50%; margin: 0 .3rem 0 .1rem;}

/* Grids of label / value */
.stats {display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.1rem 1.6rem;}
.stats div span {display: block; font-weight: 700; font-size: .82rem; margin-bottom: .2rem;}
.stats div b {font-weight: 400; font-variant-numeric: tabular-nums; color: #d9d9d9;}
.about {color: #d9d9d9; line-height: 1.55;}
.about summary {color: var(--acc); font-weight: 600; cursor: pointer; margin: .3rem 0 1rem;}

/* Lists: watchlist, positions, movers */
a.row {display: grid; grid-template-columns: 1.2fr 1fr 96px 1fr; align-items: center; gap: .8rem;
    padding: .75rem .2rem; border-bottom: 1px solid #1e2124; color: #fff !important; text-decoration: none !important;}
a.row:hover {background: #0d0f11;}
a.row.compact {grid-template-columns: 1fr 72px 1fr;}
.row b {font-weight: 700;} .row small {display: block; color: #8c8c8c; font-size: .78rem; margin-top: .1rem;}
.row .r {text-align: right; font-variant-numeric: tabular-nums;}
.pill {display: inline-block; min-width: 4.6rem; text-align: center; color: #000; font-weight: 700; font-size: .8rem;
    padding: .3rem .5rem; border-radius: .45rem; font-variant-numeric: tabular-nums;}
.cards {display: grid; grid-template-columns: repeat(5, 1fr); gap: .8rem;}
a.card {border: 1px solid #1e2124; border-radius: .8rem; padding: .9rem 1rem; color: #fff !important;
    text-decoration: none !important; display: block;}
a.card:hover {background: #0d0f11;}
.card .n {color: #8c8c8c; font-size: .78rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
.card .p {font-size: 1.15rem; font-weight: 700; margin-top: .5rem; font-variant-numeric: tabular-nums;}
.box {border: 1px solid #1e2124; border-radius: .8rem; padding: 1.1rem 1.2rem 1rem; margin-top: .2rem;}
.box-title {font-size: 1.05rem; font-weight: 700; margin-bottom: .6rem;}
.line {display: flex; justify-content: space-between; padding: .45rem 0; font-variant-numeric: tabular-nums;}
.line.total {border-top: 1px solid #2a2d31; margin-top: .3rem; padding-top: .7rem; font-weight: 700;}
.muted {color: #8c8c8c;}
.loading {border: 1px solid #1e2124; border-radius: .8rem; padding: 2.4rem; text-align: center; color: #8c8c8c;}

/* News */
a.news {display: flex; gap: 1rem; justify-content: space-between; padding: .9rem 0; border-bottom: 1px solid #1e2124;
    color: #fff !important; text-decoration: none !important;}
a.news:hover .t {color: var(--acc);}
.news .src {font-size: .78rem; font-weight: 700;} .news .src span {color: #8c8c8c; font-weight: 500;}
.news .t {font-weight: 600; margin-top: .2rem; line-height: 1.35;}
.news img {width: 76px; height: 76px; object-fit: cover; border-radius: .5rem; flex: none;}

/* Analyst ratings */
.anr {display: grid; grid-template-columns: 9rem 1fr; gap: 1.6rem; align-items: center;}
.anr .big {width: 8.5rem; height: 8.5rem; border-radius: 50%; display: flex; flex-direction: column;
    align-items: center; justify-content: center;}
.anr .big b {font-size: 1.9rem;} .anr .big small {color: #d9d9d9; font-size: .78rem;}
.bar {display: grid; grid-template-columns: 3rem 1fr 3rem; gap: .8rem; align-items: center; margin: .45rem 0;}
.bar .track {height: .55rem; background: #1e2124; border-radius: 999px; overflow: hidden;}
.bar .fill {height: 100%; border-radius: 999px;}

/* Idea lists, calendar, prediction cards */
a.idea {display: grid; grid-template-columns: 1.4fr 3.2fr 1fr; align-items: center; gap: 1rem;
    padding: .8rem .2rem; border-bottom: 1px solid #1e2124; color: #fff !important; text-decoration: none !important;}
a.idea:hover {background: #0d0f11;}
.idea small {display: block; color: #8c8c8c; font-size: .78rem;}
.chip {display: inline-block; font-size: .72rem; font-weight: 600; padding: .18rem .55rem; border-radius: 999px;
    margin: .15rem .3rem .15rem 0; white-space: nowrap;}
.score {font-weight: 800; font-size: .8rem; color: #8c8c8c;}
.cal {display: grid; grid-template-columns: 8.5rem 1fr 9rem 9rem 9rem; align-items: center; gap: 1rem;
    padding: .8rem .4rem; border-bottom: 1px solid #1e2124;}
.cal.soon {border-left: 3px solid var(--acc); background: #0d0f11;}
.cal a {color: #fff !important; text-decoration: none !important; font-weight: 700;}
.cal small {display: block; color: #8c8c8c; font-size: .78rem;}
.pred {border: 1px solid #1e2124; border-radius: .8rem; padding: 1rem 1.1rem; margin-bottom: .8rem;}
.pred a {color: #fff !important; text-decoration: none !important; font-weight: 700;}
.pred .bar {grid-template-columns: minmax(8rem, 1.2fr) 2fr 3.2rem;}
.brand {overflow: hidden; text-overflow: clip;}

/* Narrow windows: drop the wordmark so the search box never covers it */
@media (max-width: 1100px) {
    .brand {font-size: 0; } .brand::first-letter {font-size: 1.3rem;}
    .block-container {padding: .7rem 1rem 2rem;}
}
/* Phones (Streamlit stacks columns below ~640px) */
@media (max-width: 640px) {
    .block-container {padding: .5rem .75rem 3rem;}
    .brand {font-size: 1.1rem;} .brand::first-letter {font-size: inherit;}
    .mode {text-align: left;}
    .tk-name {font-size: 1.55rem;} .tk-px {font-size: 1.75rem;}
    h3 {font-size: 1.15rem !important; padding-top: 1rem !important;}
    .stats {grid-template-columns: repeat(2, 1fr); gap: .9rem 1rem;}
    .cards {grid-template-columns: repeat(2, 1fr);}
    a.row {grid-template-columns: 1fr 64px auto; gap: .5rem;}
    a.row:not(.compact) > div:nth-child(2) {display: none;}  /* volume / extra detail column */
    a.idea {grid-template-columns: 1fr auto; gap: .4rem .8rem;}
    a.idea > div:nth-child(2) {grid-column: 1 / -1; order: 3;}  /* check chips on their own line */
    .cal {grid-template-columns: 1fr 1fr; gap: .5rem 1rem;}
    .anr {grid-template-columns: 1fr; justify-items: center;}
    .anr > div:last-child {width: 100%;}
    .news img {width: 58px; height: 58px;}
    [data-testid="stButtonGroup"] button[data-variant="segmented_control"] {margin-right: .8rem;}
    [data-testid="stMetricValue"] {font-size: 1.25rem;}
}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)

stream.start()  # background price stream; no-op if already running or Alpaca is not configured

ss = st.session_state
ss.setdefault("ticker", "AAPL")
ss.setdefault("fn", HOME)
ss.setdefault("pending_order", None)
ss.setdefault("ticket_symbol", None)  # set by the options chain to trade a contract
ss.setdefault("chat", [])  # [(role, text)] for display
ss.setdefault("chat_api", [])  # full message history sent to Claude


# ---------- cached data ----------
@st.cache_data(ttl=30, show_spinner=False)
def c_quote(s): return data.quote(s)
@st.cache_data(ttl=30, show_spinner=False)
def c_quotes(syms): return data.quotes(list(syms))
@st.cache_data(ttl=300, show_spinner=False)
def c_history(s, period, interval): return data.history(s, period, interval)
@st.cache_data(ttl=900, show_spinner=False)
def c_info(s): return data.info(s)
@st.cache_data(ttl=300, show_spinner=False)
def c_news(s): return data.news(s)
@st.cache_data(ttl=3600, show_spinner=False)
def c_fin(s, stmt, q): return data.financials(s, stmt, q)
@st.cache_data(ttl=3600, show_spinner=False)
def c_recs(s): return data.recommendations(s)
@st.cache_data(ttl=120, show_spinner=False)
def c_screen(name): return data.screen(name)
@st.cache_data(ttl=900, show_spinner=False)
def c_filings(s): return sources.sec_filings(s)
@st.cache_data(ttl=3600, show_spinner=False)
def c_insiders(s): return sources.insider_transactions(s)
@st.cache_data(ttl=3600, show_spinner=False)
def c_surprises(s): return sources.earnings_surprises(s)
@st.cache_data(ttl=3600, show_spinner=False)
def c_calendar(days): return sources.earnings_calendar(days)
@st.cache_data(ttl=3600, show_spinner=False)
def c_fmp(endpoint, s): return sources.fmp(endpoint, s)
@st.cache_data(ttl=3600, show_spinner=False)
def c_fred(series_id): return sources.fred_series(series_id)
@st.cache_data(ttl=3600, show_spinner=False)
def c_expiries(s): return data.option_expirations(s)
@st.cache_data(ttl=60, show_spinner=False)
def c_chain(s, expiry): return data.option_chain(s, expiry)
@st.cache_data(ttl=60, show_spinner=False)
def c_sparks(syms): return data.sparklines(list(syms))
@st.cache_data(ttl=60, show_spinner=False)
def c_port_history(broker_name, period): return c_brokers()[0][broker_name].portfolio_history(period)
@st.cache_data(ttl=6 * 3600, show_spinner=False)
def c_upcoming(syms): return sources.upcoming_earnings(list(syms))
@st.cache_data(ttl=600, show_spinner=False)
def c_predictions(): return predictions.all_events()
@st.cache_data(ttl=60, show_spinner=False)
def c_held():
    """Stock symbols held at any connected broker (options left out)."""
    held = []
    for b in c_brokers()[0].values():
        try:
            held += [p["symbol"] for p in b.positions()]
        except Exception:
            pass
    return [s for s in dict.fromkeys(held) if not OrderRequest(s, "buy", 1).is_option]
@st.cache_resource(show_spinner="Connecting to brokers...")
def c_brokers(): return connect_all()


# ---------- helpers ----------
def big(n) -> str:
    if n is None or pd.isna(n):
        return "-"
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(n) >= div:
            return f"{n / div:,.2f}{suf}"
    return f"{n:,.2f}"


def num(n, fmt="{:,.2f}") -> str:
    return "-" if n is None or pd.isna(n) else fmt.format(n)


def run_command():
    """Command bar: 'AAPL GP', 'MSFT', 'PORT' ..."""
    parts = ss.cmd.upper().split()
    ss.cmd = ""
    for p in parts:
        if p in FUNCTIONS:
            ss.fn = p
        else:
            ss.ticker = p
            ss.pending_order = None
            ss.ticket_symbol = None


def usd(n, sign: bool = False) -> str:
    if n is None or pd.isna(n):
        return "-"
    # "&#36;" rather than "$": two dollar signs in one markdown block are read as a LaTeX formula.
    return f"{'+' if sign and n > 0 else '-' if n < 0 else ''}&#36;{abs(n):,.2f}"


def link(symbol: str) -> str:
    """URL that opens a symbol's overview (list rows and cards are plain links)."""
    return f"?t={symbol}"


# ---------- header ----------
# Clicking a row in a list loads ?t=SYMBOL; open that stock, then tidy the address bar.
if "t" in st.query_params or "f" in st.query_params:  # ?f=CODE opens a screen directly, e.g. ?f=SPX
    if "t" in st.query_params:
        ss.ticker, ss.fn = st.query_params["t"].upper(), "DES"
        ss.pending_order = ss.ticket_symbol = None
    if st.query_params.get("f", "").upper() in FUNCTIONS:
        ss.fn = st.query_params["f"].upper()
    st.query_params.clear()

sym = ss.ticker
fn = ss.fn if ss.fn in FUNCTIONS else HOME
group = GROUP_OF[fn]
# The two nav widgets mirror `fn`, so typed commands and buttons that change screen stay in sync.
ss.nav_group, ss.nav_item = group, fn
STOCK_HEADER = group == "Stock" or fn in ("ALRT", "AI")

q = None
if STOCK_HEADER or fn == "ORD":
    try:
        q = c_quote(sym)
    except Exception:
        q = None
ACC = ORANGE  # brand accent: buttons, tabs, highlights. Gains and losses stay green / red.
st.markdown(f"<style>:root {{--acc: {ACC};}}</style>", unsafe_allow_html=True)


def pick_group():
    ss.fn = next(iter(NAV[ss.nav_group or group]))


def pick_item():
    ss.fn = ss.nav_item or fn


top = st.columns([1.1, 3.2, 5, 1.4], vertical_alignment="center")
top[0].markdown(f"<a class='brand' href='?f={HOME}' target='_self' style='text-decoration:none;display:block'>▮ Terminal</a>",
               unsafe_allow_html=True)
top[1].text_input(
    "Search", key="cmd", on_change=run_command, placeholder="Search", label_visibility="collapsed",
    icon=":material/search:", help="Type a ticker (NVDA), a screen code (GP), or both (MSFT FA) and press Enter",
)
top[2].segmented_control("Section", list(NAV), key="nav_group", on_change=pick_group, label_visibility="collapsed")
mode_color = RED if config.LIVE else GREEN
top[3].markdown(
    f"<div class='mode'><span style='color:{mode_color};background:{mode_color}22'>{config.MODE_LABEL}</span></div>",
    unsafe_allow_html=True,
)
st.pills("Screen", list(NAV[group]), key="nav_item", format_func=lambda c: NAV[group][c], on_change=pick_item,
         label_visibility="collapsed")
st.divider()

brokers, broker_errors = c_brokers()


def stream_badge() -> str:
    state, why = stream.status()
    label, color = {"live": ("Live", GREEN), "connecting": ("Delayed", AMBER)}.get(state, ("Snapshot", MUTED))
    return f"<span title='{why}'><span class='dot' style='background:{color}'></span>{label}</span>"


@st.fragment(run_every=1)
def live_header(base: dict, name: str):
    """Name, price and today's move; redrawn every second from the background price stream."""
    q = data.with_live(base)
    color = GREEN if (q["change"] or 0) >= 0 else RED
    quote = f" · Bid {usd(q['bid'])} × Ask {usd(q['ask'])}" if q.get("bid") else ""
    st.markdown(
        f"<div class='tk-name'>{name or sym}</div>"
        f"<div class='tk-px'>{usd(q['last'])}</div>"
        f"<div class='tk-chg' style='color:{color}'>{usd(q['change'], sign=True)} "
        f"({num(q['change_pct'], '{:+.2f}%')})<small>Today</small></div>"
        f"<div class='tk-sub'>{sym}{quote} · {stream_badge()}</div>",
        unsafe_allow_html=True,
    )


@st.fragment(run_every=15)
def alert_watch():
    for a in alerts.check():
        st.toast(f"ALERT: {a['symbol']} is {a['direction']} {a['price']:,.2f} (now {a['triggered']:,.2f})", icon="🔔")


alert_watch()
company = ""
if STOCK_HEADER:
    if q is None:
        st.error(f"No market data for '{sym}'. Check the ticker symbol.")
    else:
        try:
            company = c_info(sym).get("shortName") or ""
        except Exception:
            pass
        if fn != "DES":  # the overview places the header beside its order card instead
            live_header(q, company)

RANGES = {"1D": ("1d", "5m"), "1W": ("5d", "15m"), "1M": ("1mo", "1h"), "3M": ("3mo", "1d"),
          "YTD": ("ytd", "1d"), "1Y": ("1y", "1d"), "5Y": ("5y", "1wk"), "MAX": ("max", "1mo")}
NO_TOOLBAR = {"displayModeBar": False}


def style_fig(fig, height: int, **layout):
    layout.setdefault("margin", dict(l=0, r=0, t=10, b=0))
    fig.update_layout(template="plotly_dark", paper_bgcolor=CLEAR, plot_bgcolor=CLEAR, height=height,
                      font=dict(color=MUTED, family="Inter"),
                      hoverlabel=dict(bgcolor="#1e2124", bordercolor="#1e2124", font_color="#fff"), **layout)
    fig.update_xaxes(gridcolor=LINE, zeroline=False)
    fig.update_yaxes(gridcolor=LINE, zeroline=False)
    return fig


def skip_closed_hours(fig, rng: str):
    if RANGES[rng][1] in ("5m", "15m", "1h"):
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"]), dict(bounds=[16, 9.5], pattern="hour")])


def line_chart(series: pd.Series, height: int, color: str, baseline: float | None = None, rng: str | None = None):
    """Robinhood-style chart: one line, no axes or grid, a crosshair and price + date on hover."""
    idx = pd.DatetimeIndex(series.index)
    intraday = bool((idx != idx.normalize()).any())  # bars with a time of day, so show the time too
    when = "%b %d, %Y · %I:%M %p" if intraday else "%a, %b %d, %Y"
    fig = go.Figure(go.Scatter(x=series.index, y=series.values, mode="lines", line=dict(color=color, width=2),
                               hovertemplate=f"<b>$%{{y:,.2f}}</b><br>%{{x|{when}}}<extra></extra>"))
    if baseline:
        fig.add_hline(y=baseline, line=dict(color="#4a4d52", width=1, dash="dot"))
    style_fig(fig, height, showlegend=False, hovermode="x", margin=dict(l=0, r=0, t=6, b=0))
    fig.update_xaxes(visible=False, showspikes=True, spikemode="across", spikethickness=1, spikecolor="#4a4d52",
                     spikedash="solid")
    fig.update_yaxes(visible=False)
    if rng:
        skip_closed_hours(fig, rng)
    st.plotly_chart(fig, width="stretch", config=NO_TOOLBAR)


def spark_svg(vals: list[float], color: str, baseline: float | None = None, w: int = 96, h: int = 34) -> str:
    if not vals or len(vals) < 2:
        return ""
    pts = vals + ([baseline] if baseline else [])
    lo, hi = min(pts), max(pts)
    span = (hi - lo) or 1

    def y(v):
        return h - 2 - (v - lo) / span * (h - 4)

    line = " ".join(f"{i * w / (len(vals) - 1):.1f},{y(v):.1f}" for i, v in enumerate(vals))
    base = (f"<line x1='0' x2='{w}' y1='{y(baseline):.1f}' y2='{y(baseline):.1f}' stroke='#4a4d52' "
            "stroke-dasharray='1 3'/>") if baseline else ""
    return (f"<svg width='{w}' height='{h}' viewBox='0 0 {w} {h}'>{base}"
            f"<polyline fill='none' stroke='{color}' stroke-width='1.6' points='{line}'/></svg>")


def stock_rows(rows: list[dict], compact: bool = False) -> str:
    """List rows like Robinhood's watchlist: symbol, sparkline, price and a coloured change pill.
    Each row: symbol, last, change_pct, optional prev, spark, sub, extra (right-hand detail)."""
    html = []
    for r in rows:
        pct = r.get("change_pct")
        color = RED if (pct or 0) < 0 else GREEN
        sub = f"<small>{r['sub']}</small>" if r.get("sub") else ""
        extra = "" if compact else f"<div class='r'>{r.get('extra', '')}</div>"
        html.append(
            f"<a class='row{' compact' if compact else ''}' href='{link(r['symbol'])}' target='_self'>"
            f"<div><b>{r['symbol']}</b>{sub}</div>{extra}"
            f"<div>{spark_svg(r.get('spark') or [], color, r.get('prev'), w=72 if compact else 96)}</div>"
            f"<div class='r'><b>{usd(r.get('last'))}</b><br>"
            f"<span class='pill' style='background:{color}'>{num(pct, '{:+.2f}%')}</span></div></a>"
        )
    # Wrapped in a block element so markdown passes it through as raw HTML instead of splitting the links.
    return "<div>" + "".join(html) + "</div>"


# ---------- screens ----------
def screen_des():
    i = c_info(sym)
    left, right = st.columns([2.3, 1], gap="large")
    with left:
        if q:
            live_header(q, company)
        chart_box = st.container()  # filled after the range tabs below it are read
        rng = st.segmented_control("Range", list(RANGES), default="1D", key="des_range",
                                   label_visibility="collapsed") or "1D"
        with chart_box:
            df = c_history(sym, *RANGES[rng])
            if df.empty:
                st.markdown("<div class='loading'>No price history for this range yet.</div>", unsafe_allow_html=True)
            elif rng == "1D":
                line_chart(df.Close, 330, RED if (q or {}).get("change", 0) < 0 else GREEN, (q or {}).get("prev_close"), rng)
            else:
                line_chart(df.Close, 330, GREEN if df.Close.iloc[-1] >= df.Close.iloc[0] else RED, None, rng)
        if not (i.get("longName") or i.get("shortName")):
            st.caption("No company profile available for this symbol.")
            return
        about_section(i)
        key_stats(i)
        st.subheader("News")
        news_list(c_news(sym)[:6])
        st.subheader("Analyst ratings")
        analyst_block(i)
    with right:
        with st.container(border=True):
            order_ticket()
        st.write("")
        st.markdown("<div class='box-title'>Watchlist</div>", unsafe_allow_html=True)
        watchlist_panel(tuple(config.WATCHLIST), compact=True)


def about_section(i: dict):
    st.subheader("About")
    text = htmllib.escape(i.get("longBusinessSummary") or "")
    if text:
        cut = text.find(". ", 320)
        head, rest = (text[: cut + 1], text[cut + 1:]) if cut > 0 else (text, "")
        more = f"<details><summary>Show more</summary>{rest}</details>" if rest else ""
        st.markdown(f"<div class='about'>{head}{more}</div>", unsafe_allow_html=True)
    hq = ", ".join(x for x in (i.get("city"), i.get("state") or i.get("country")) if x)
    site = i.get("website")
    facts = [("Sector", i.get("sector") or "-"), ("Industry", i.get("industry") or "-"),
             ("Employees", num(i.get("fullTimeEmployees"), "{:,.0f}")), ("Headquarters", hq or "-")]
    if site:
        facts.append(("Website", f"<a href='{site}' target='_blank' style='color:var(--acc)'>{site.split('//')[-1]}</a>"))
    stats_grid(facts)


def stats_grid(pairs: list[tuple[str, str]]):
    st.markdown("<div class='stats'>" + "".join(f"<div><span>{k}</span><b>{v}</b></div>" for k, v in pairs)
                + "</div>", unsafe_allow_html=True)


def key_stats(i: dict):
    st.subheader("Key statistics")
    qq = q or {}
    pct = lambda v: num(v, "{:.1%}")
    stats_grid([
        ("Market cap", big(i.get("marketCap"))), ("Price-earnings ratio", num(i.get("trailingPE"))),
        ("Forward P/E", num(i.get("forwardPE"))), ("Dividend yield", num(i.get("dividendYield"), "{:.2f}%")),
        ("Average volume", big(i.get("averageVolume"))), ("Volume", big(qq.get("volume"))),
        ("High today", usd(qq.get("day_high"))), ("Low today", usd(qq.get("day_low"))),
        ("Open price", usd(i.get("open"))), ("Previous close", usd(qq.get("prev_close"))),
        ("52 week high", usd(qq.get("year_high"))), ("52 week low", usd(qq.get("year_low"))),
        ("Revenue (ttm)", big(i.get("totalRevenue"))), ("Revenue growth", pct(i.get("revenueGrowth"))),
        ("Gross margin", pct(i.get("grossMargins"))), ("Profit margin", pct(i.get("profitMargins"))),
        ("Return on equity", pct(i.get("returnOnEquity"))), ("Free cash flow", big(i.get("freeCashflow"))),
        ("Debt / equity", num(i.get("debtToEquity"))), ("Beta", num(i.get("beta"))),
        ("Price / sales", num(i.get("priceToSalesTrailing12Months"))), ("Price / book", num(i.get("priceToBook"))),
        ("EV / EBITDA", num(i.get("enterpriseToEbitda"))), ("Short % of float", pct(i.get("shortPercentOfFloat"))),
    ])


def analyst_block(i: dict):
    recs = c_recs(sym)
    if recs.empty or "period" not in recs:
        st.caption("No analyst ratings for this symbol.")
        return
    now = recs[recs["period"] == "0m"]
    r = (now if not now.empty else recs).iloc[0]
    counts = {"Buy": r.get("strongBuy", 0) + r.get("buy", 0), "Hold": r.get("hold", 0),
              "Sell": r.get("sell", 0) + r.get("strongSell", 0)}
    total = sum(counts.values())
    if not total:
        st.caption("No analyst ratings for this symbol.")
        return
    share = {k: v / total * 100 for k, v in counts.items()}
    lead = max(share, key=share.get)
    lead_color = {"Buy": GREEN, "Hold": "#d9d9d9", "Sell": RED}[lead]
    bars = "".join(
        f"<div class='bar'><span>{k}</span><div class='track'><div class='fill' style='width:{v:.0f}%;"
        f"background:{ {'Buy': GREEN, 'Hold': '#8c8c8c', 'Sell': RED}[k]}'></div></div>"
        f"<span class='r'>{v:.0f}%</span></div>" for k, v in share.items())
    target = ""
    if i.get("targetMeanPrice"):
        target = (f"<div class='muted' style='margin-top:1rem'>Average price target <b style='color:#fff'>"
                  f"{usd(i['targetMeanPrice'])}</b> · low {usd(i.get('targetLowPrice'))} · "
                  f"high {usd(i.get('targetHighPrice'))}</div>")
    st.markdown(
        f"<div class='anr'><div class='big' style='background:{lead_color}22;color:{lead_color}'>"
        f"<b>{share[lead]:.0f}%</b><small>{lead} · {total} ratings</small></div><div>{bars}</div></div>{target}",
        unsafe_allow_html=True)


def ago(published) -> str:
    try:
        mins = (pd.Timestamp.now(tz="UTC") - pd.Timestamp(published, tz="UTC")).total_seconds() / 60
    except Exception:
        return str(published or "")
    return f"{max(int(mins), 1)}m" if mins < 60 else f"{int(mins / 60)}h" if mins < 1440 else f"{int(mins / 1440)}d"


def news_list(items: list[dict]):
    if not items:
        st.caption("No recent news for this symbol.")
        return
    html = []
    for n in items:
        img = f"<img src='{n['thumb']}' loading='lazy'>" if n.get("thumb") else ""
        html.append(
            f"<a class='news' href='{n['url']}' target='_blank'><div>"
            f"<div class='src'>{htmllib.escape(n['publisher'] or '')} <span>{ago(n['published'])}</span></div>"
            f"<div class='t'>{htmllib.escape(n['title'])}</div></div>{img}</a>")
    st.markdown("<div>" + "".join(html) + "</div>", unsafe_allow_html=True)


def watch_data(symbols: tuple) -> list[dict]:
    """Rows for stock_rows(): cached quotes, live last price and today's sparkline."""
    df = c_quotes(symbols)
    live = data.live_prices(list(symbols))
    sparks = c_sparks(symbols)
    rows = []
    for r in df.to_dict("records"):
        s = r["symbol"]
        last = live.get(s, {}).get("last", r.get("last"))
        prev = r.get("prev_close")
        rows.append({
            "symbol": s, "last": last, "prev": prev,
            "change_pct": (last / prev - 1) * 100 if last and prev else r.get("change_pct"),
            "spark": (sparks.get(s) or []) + ([last] if last and sparks.get(s) else []),
            "volume": r.get("volume"), "market_cap": r.get("market_cap"),
            "year_low": r.get("year_low"), "year_high": r.get("year_high"),
        })
    return rows


@st.fragment(run_every=2)
def watchlist_panel(symbols: tuple, compact: bool = False):
    rows = watch_data(symbols)
    if not compact:
        for r in rows:
            r["extra"] = (f"<span class='muted'>Vol</span> {big(r['volume'])}<small>Mkt cap {big(r['market_cap'])}</small>")
    st.markdown(stock_rows(rows, compact=compact), unsafe_allow_html=True)


def order_ticket(symbol_input: bool = False):
    """Robinhood-style order card. Every order goes through Review -> Submit before it is sent."""
    if not brokers:
        broker_notices()
        return
    names = list(brokers)
    bname = st.selectbox("Account", names) if len(names) > 1 else names[0]
    tsym = st.text_input("Symbol", value=ss.ticket_symbol or sym).strip().upper() if symbol_input else sym
    is_opt = bool(tsym) and OrderRequest(tsym, "buy", 1).is_option
    ref = data.with_live(q)["last"] if q and tsym == sym else None  # reference price for defaults and the estimate
    side = st.segmented_control("Side", ["buy", "sell"], default="buy", key="ticket_side", label_visibility="collapsed",
                                format_func=lambda s: f"{s.title()} {'' if is_opt else tsym}") or "buy"
    kinds = {"market": "Market order", "limit": "Limit order", "stop": "Stop order"}
    otype = st.selectbox("Order type", ["limit", "market"] if is_opt else ["market", "limit", "stop"],
                         format_func=kinds.get)
    qty = st.number_input("Contracts (100 shares each)" if is_opt else "Shares", min_value=0.0, value=1.0, step=1.0)
    px = None
    if otype != "market":
        px = st.number_input(f"{otype.title()} price", min_value=0.0, value=float(round(ref or 0, 2)), step=0.01)
    tp = sl = None
    with st.expander("Advanced"):
        tif = st.selectbox("Time in force", ["day"] if is_opt else ["day", "gtc"],
                           format_func={"day": "Good for day", "gtc": "Good till canceled"}.get)
        if not is_opt and st.toggle("Attach exits (bracket)", help="Adds a take-profit and/or stop-loss order that "
                                    "activates once this order fills. Alpaca only."):
            c = st.columns(2)
            tp = c[0].number_input("Take profit at", min_value=0.0, value=0.0, step=0.01, help="0 = none") or None
            sl = c[1].number_input("Stop loss at", min_value=0.0, value=0.0, step=0.01, help="0 = none") or None
    unit = px or ref
    est = qty * unit * (100 if is_opt else 1) if unit else None
    st.markdown(
        (f"<div class='line'><span>Market price</span><b style='color:var(--acc)'>{usd(ref)}</b></div>" if ref else "")
        + f"<div class='line total'><span>Estimated {'cost' if side == 'buy' else 'credit'}</span>"
        f"<span>{usd(est) if est else '-'}</span></div>", unsafe_allow_html=True)
    if st.button("Review order", type="primary", width="stretch",
                 disabled=not tsym or qty <= 0 or (otype != "market" and not px)):
        ss.pending_order = (bname, OrderRequest(tsym, side, qty, otype, px if otype == "limit" else None,
                                                px if otype == "stop" else None, tif, tp, sl))
    if ss.pending_order:
        pb, req = ss.pending_order
        unit_px = req.limit_price or req.stop_price or (ref if req.symbol == tsym else None)
        value = usd(req.qty * unit_px * (100 if req.is_option else 1)) if unit_px else "unknown (market order)"
        with st.container(border=True):
            st.markdown(f"**Confirm {config.MODE_LABEL.lower()} order via {pb}**  \n{req.describe()}  \n"
                        f"Estimated value: {value}")
            if config.LIVE:
                st.error("This uses real money.")
            c = st.columns(2)
            if c[0].button("Submit order", type="primary", width="stretch"):
                try:
                    oid = brokers[pb].submit_order(req)
                    st.success(f"Order sent. Id {oid}")
                except Exception as e:
                    st.error(f"Order rejected: {e}")
                ss.pending_order = None
            if c[1].button("Edit", width="stretch"):
                ss.pending_order = None
                st.rerun()
    try:
        bp = brokers[bname].account()["buying_power"]
        st.markdown(f"<div class='muted' style='text-align:center;margin-top:.6rem'>{usd(bp)} buying power available"
                    "</div>", unsafe_allow_html=True)
    except Exception:
        pass


INDICATORS = ["SMA 20", "SMA 50", "SMA 200", "Bollinger bands", "RSI", "MACD"]


def screen_gp():
    c = st.columns([5, 4, 2], vertical_alignment="center")
    rng = c[0].segmented_control("Range", list(RANGES), default="1Y", label_visibility="collapsed") or "1Y"
    chosen = c[1].multiselect("Indicators", INDICATORS, default=["SMA 50", "SMA 200"],
                              label_visibility="collapsed", placeholder="Add indicators")
    compare = c[2].toggle("vs S&P 500", help="Show both as % change over the range (SPY tracks the S&P 500)")
    period, interval = RANGES[rng]
    df = c_history(sym, period, interval)
    if df.empty:
        st.info("No price history for this range.")
        return
    if compare:
        compare_chart(df, rng)
        return
    # Daily charts: compute indicators on 5 years so long averages are filled from the first bar shown.
    full = c_history(sym, "5y", "1d") if interval == "1d" and rng != "MAX" else df
    close = full.Close
    clip = lambda s: s.reindex(df.index)

    panels = [p for p in ("RSI", "MACD") if p in chosen]
    heights = [0.62, 0.14] + [0.12] * len(panels)
    fig = make_subplots(rows=2 + len(panels), cols=1, shared_xaxes=True, vertical_spacing=0.025,
                        row_heights=[h / sum(heights) for h in heights])
    fig.add_trace(go.Candlestick(x=df.index, open=df.Open, high=df.High, low=df.Low, close=df.Close, name=sym,
                                 increasing_line_color=GREEN, decreasing_line_color=RED), row=1, col=1)
    for name, colr in zip(("SMA 20", "SMA 50", "SMA 200"), ("#4da3ff", AMBER, "#c77dff")):
        if name in chosen:
            fig.add_trace(go.Scatter(x=df.index, y=clip(ind.sma(close, int(name.split()[1]))), name=name,
                                     line=dict(color=colr, width=1.2)), row=1, col=1)
    if "Bollinger bands" in chosen:
        lower, mid, upper = (clip(s) for s in ind.bollinger(close))
        band = dict(color="#8c8c8c", width=1)
        fig.add_trace(go.Scatter(x=df.index, y=upper, name="Bollinger upper", line=band), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=lower, name="Bollinger lower", line=band, fill="tonexty",
                                 fillcolor="rgba(140,140,140,0.08)"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=mid, name="Bollinger mid", line=dict(color="#8c8c8c", width=1,
                                                                                 dash="dot")), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df.Volume, name="Volume", marker_color="#3b4352"), row=2, col=1)
    row = 3
    if "RSI" in chosen:
        fig.add_trace(go.Scatter(x=df.index, y=clip(ind.rsi(close)), name="RSI 14", line=dict(color=AMBER, width=1.2)),
                      row=row, col=1)
        for level in (30, 70):
            fig.add_hline(y=level, line=dict(color="#4a4d52", width=1, dash="dot"), row=row, col=1)
        fig.update_yaxes(range=[0, 100], row=row, col=1, title_text="RSI")
        row += 1
    if "MACD" in chosen:
        line, sig, hist = (clip(s) for s in ind.macd(close))
        fig.add_trace(go.Bar(x=df.index, y=hist, name="MACD histogram",
                             marker_color=[GREEN if v >= 0 else RED for v in hist.fillna(0)]), row=row, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=line, name="MACD", line=dict(color="#4da3ff", width=1.2)), row=row, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=sig, name="Signal", line=dict(color=AMBER, width=1.2)), row=row, col=1)
        fig.update_yaxes(title_text="MACD", row=row, col=1)
    style_fig(fig, 640 + 150 * len(panels), xaxis_rangeslider_visible=False, legend=dict(orientation="h", y=1.04),
              hovermode="x unified")
    skip_closed_hours(fig, rng)
    st.plotly_chart(fig, width="stretch")
    st.caption("RSI above 70 is often read as overbought and below 30 as oversold. MACD crossing above its signal "
               "line is a common momentum signal. Bollinger bands mark two standard deviations around a 20-day average.")


def compare_chart(df: pd.DataFrame, rng: str):
    """The stock against SPY, both as % change from the start of the range."""
    spy = c_history("SPY", *RANGES[rng])
    fig = go.Figure()
    lines = [(sym, df.Close, ACC)] + ([("S&P 500 (SPY)", spy.Close, "#8c8c8c")] if sym != "SPY" and not spy.empty else [])
    for name, s, colr in lines:
        pct = (s / s.iloc[0] - 1) * 100
        fig.add_trace(go.Scatter(x=s.index, y=pct, name=name, line=dict(color=colr, width=2),
                                 hovertemplate=f"{name} %{{y:+.2f}}%<extra></extra>"))
    fig.add_hline(y=0, line=dict(color="#4a4d52", width=1, dash="dot"))
    style_fig(fig, 560, hovermode="x unified", legend=dict(orientation="h", y=1.06), yaxis_ticksuffix="%")
    skip_closed_hours(fig, rng)
    st.plotly_chart(fig, width="stretch")
    if len(lines) == 2:
        a, b = ((s.iloc[-1] / s.iloc[0] - 1) * 100 for _, s, _ in lines)
        verdict = "ahead of" if a > b else "behind"
        st.markdown(f"<div class='muted'>{sym} <b style='color:#fff'>{a:+.2f}%</b> vs S&P 500 <b style='color:#fff'>"
                    f"{b:+.2f}%</b> over this range: {abs(a - b):.2f} points {verdict} the market.</div>",
                    unsafe_allow_html=True)


def screen_fa():
    c = st.columns([4, 2, 6])
    stmt = c[0].segmented_control("Statement", ["income", "balance", "cashflow"], default="income",
                                  format_func=str.title, label_visibility="collapsed") or "income"
    quarterly = c[1].toggle("Quarterly")
    df = c_fin(sym, stmt, quarterly)
    if df.empty:
        st.info("No financial statements available for this symbol.")
        return
    st.dataframe(df.map(big), height=680, width="stretch")


def screen_news():
    items = c_news(sym)
    news_list(items)


def screen_anr():
    i = c_info(sym)
    left, right = st.columns([1.3, 1], gap="large")
    with left:
        st.subheader("Analyst ratings")
        analyst_block(i)
    with right:
        st.subheader("How ratings changed")
        recs = c_recs(sym)
        if recs.empty:
            st.caption("No analyst rating history for this symbol.")
            return
        labels = {"strongBuy": "Strong buy", "buy": "Buy", "hold": "Hold", "sell": "Sell", "strongSell": "Strong sell"}
        colors = ("#00c805", "#5be36b", "#5c5f63", "#ff8a50", RED)
        fig = go.Figure()
        for (col, name), colr in zip(labels.items(), colors):
            if col in recs.columns:
                fig.add_trace(go.Bar(x=recs["period"], y=recs[col], name=name, marker_color=colr))
        style_fig(fig, 320, barmode="stack", xaxis_title="Months ago (0m = this month)",
                  legend=dict(orientation="h", y=-0.3))
        st.plotly_chart(fig, width="stretch", config=NO_TOOLBAR)


def needs_key(name: str, value: str, where: str) -> bool:
    if not value:
        st.info(f"Add {name} to .env to use this screen (free key from {where}), then restart the app.")
    return not value


def screen_val():
    if needs_key("FMP_API_KEY", config.FMP_API_KEY, "financialmodelingprep.com"):
        return
    try:
        dcf = c_fmp("discounted-cash-flow", sym)
        scores = c_fmp("financial-scores", sym)
        rating = c_fmp("ratings-snapshot", sym)
        target = c_fmp("price-target-consensus", sym)
    except Exception as e:
        st.error(f"Financial Modeling Prep: {sources.clean_error(e)}")
        return
    last = (q or {}).get("last")
    fair = dcf.get("dcf")
    m = st.columns(6)
    m[0].metric("DCF fair value", num(fair), None if not (fair and last) else f"{(fair / last - 1) * 100:+.1f}% vs price")
    m[1].metric("Rating", rating.get("rating", "-"), help="FMP's composite grade from the sub-scores below")
    m[2].metric("Piotroski score", num(scores.get("piotroskiScore"), "{:.0f} / 9"), help="Financial strength, 0-9. 8-9 is strong.")
    m[3].metric("Altman Z-score", num(scores.get("altmanZScore")), help="Bankruptcy risk. Above 3 is safe, below 1.8 is distress.")
    tc = target.get("targetConsensus")
    m[4].metric("Analyst target", num(tc), None if not (tc and last) else f"{(tc / last - 1) * 100:+.1f}% vs price")
    m[5].metric("Target range", f"{num(target.get('targetLow'), '{:,.0f}')}-{num(target.get('targetHigh'), '{:,.0f}')}")
    st.caption("DCF is one model's estimate with its own assumptions; it often differs widely from the market price.")
    c = st.columns(3)
    tables = (("Rating sub-scores (1-5)", rating), ("Ratios (ttm)", c_fmp("ratios-ttm", sym)),
              ("Key metrics (ttm)", c_fmp("key-metrics-ttm", sym)))
    for col, (title, rec) in zip(c, tables):
        rows = [(k, v) for k, v in rec.items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
        col.caption(title)
        col.dataframe(pd.DataFrame(rows, columns=["Metric", "Value"]), hide_index=True, width="stretch", height=520,
                      column_config={"Value": st.column_config.NumberColumn(format="compact")})


def screen_ern():
    if needs_key("FINNHUB_API_KEY", config.FINNHUB_API_KEY, "finnhub.io"):
        return
    left, right = st.columns([2, 3])
    with left:
        st.subheader(f"{sym} vs estimates")
        try:
            s = c_surprises(sym)
        except Exception as e:
            s = pd.DataFrame()
            st.error(f"Finnhub: {sources.clean_error(e)}")
        if s.empty:
            st.caption("No earnings history for this symbol.")
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=s["period"], y=s["estimate"], mode="markers", name="Estimate",
                                     marker=dict(color="#888", size=11, symbol="circle-open")))
            fig.add_trace(go.Scatter(x=s["period"], y=s["actual"], mode="markers", name="Actual", marker=dict(
                size=11, color=[GREEN if (a or 0) >= (e or 0) else RED for a, e in zip(s["actual"], s["estimate"])])))
            style_fig(fig, 300, yaxis_title="EPS")
            st.plotly_chart(fig, width="stretch")
            st.dataframe(s[["period", "estimate", "actual", "surprisePercent"]], hide_index=True, width="stretch",
                         column_config={"surprisePercent": st.column_config.NumberColumn("surprise", format="%+.1f%%")})
    with right:
        st.subheader("Upcoming earnings")
        c = st.columns(2)
        days = c[0].segmented_control("Window", [7, 14, 30], default=14, format_func=lambda d: f"{d} days",
                                      label_visibility="collapsed") or 14
        only_est = c[1].toggle("Only with estimates", value=True, help="Hides small companies no analyst covers")
        try:
            cal = c_calendar(days)
        except Exception as e:
            st.error(f"Finnhub: {sources.clean_error(e)}")
            return
        if not cal.empty and only_est:
            cal = cal[cal["epsEstimate"].notna()]
        if cal.empty:
            st.caption("No earnings in this window.")
            return
        cal = cal.assign(hour=cal["hour"].map({"bmo": "before open", "amc": "after close", "dmh": "during hours"}))
        st.dataframe(cal[["date", "hour", "symbol", "epsEstimate", "revenueEstimate"]], hide_index=True, width="stretch",
                     height=600, column_config={
                         "epsEstimate": st.column_config.NumberColumn("EPS est.", format="%.2f"),
                         "revenueEstimate": st.column_config.NumberColumn("revenue est.", format="compact")})


def screen_sec():
    left, right = st.columns([3, 2])
    with left:
        st.subheader("SEC filings")
        try:
            f = c_filings(sym)
        except Exception as e:
            f = pd.DataFrame()
            st.error(f"SEC EDGAR: {sources.clean_error(e)}")
        if f.empty:
            st.caption("No SEC filings found. Only US-registered companies file with the SEC.")
        else:
            kinds = {"Reports (10-K, 10-Q)": ["10-K", "10-Q"], "Events (8-K)": ["8-K"], "Insider (Form 4)": ["4"],
                     "Proxy": ["DEF 14A"], "All": None}
            kind = st.segmented_control("Type", list(kinds), default="Reports (10-K, 10-Q)",
                                        label_visibility="collapsed") or "All"
            if kinds[kind]:
                f = f[f["form"].isin(kinds[kind])]
            st.dataframe(f, hide_index=True, width="stretch", height=600,
                         column_config={"url": st.column_config.LinkColumn("document", display_text="open")})
    with right:
        st.subheader("Insider transactions")
        if needs_key("FINNHUB_API_KEY", config.FINNHUB_API_KEY, "finnhub.io"):
            return
        try:
            ins = c_insiders(sym)
        except Exception as e:
            st.error(f"Finnhub: {sources.clean_error(e)}")
            return
        if ins.empty:
            st.caption("No insider transactions reported.")
            return
        if st.toggle("Open-market buys and sells only", value=True, help="Hides grants, option exercises and tax withholding"):
            ins = ins[ins["transactionCode"].isin(["P", "S"])]
        ins = ins.assign(type=ins["transactionCode"].map({"P": "BUY", "S": "SELL"}).fillna(ins["transactionCode"]),
                         value=ins["change"].abs() * ins["transactionPrice"])
        st.dataframe(ins[["transactionDate", "name", "type", "change", "transactionPrice", "value"]], hide_index=True,
                     width="stretch", height=560, column_config={
                         "transactionDate": "date", "change": st.column_config.NumberColumn("shares", format="localized"),
                         "transactionPrice": st.column_config.NumberColumn("price", format="%.2f"),
                         "value": st.column_config.NumberColumn(format="compact")})


def screen_eco():
    if needs_key("FRED_API_KEY", config.FRED_API_KEY, "fred.stlouisfed.org/docs/api/api_key.html"):
        return
    events, errors = c_predictions()
    fed = predictions.matching(events, "Fed & rates")[:2]
    if fed:
        st.markdown("<div class='box-title'>What markets expect</div>", unsafe_allow_html=True)
        for col, e in zip(st.columns(len(fed)), fed):
            col.markdown(pred_card(e, n=4), unsafe_allow_html=True)
    elif errors:
        st.caption("Prediction-market odds would show here, but Kalshi and Polymarket can't be reached from this "
                   "network (see Market → Predictions).")
    names = list(sources.FRED_SERIES)
    for row in (names[:5], names[5:]):
        for col, name in zip(st.columns(5), row):
            try:
                s = c_fred(sources.FRED_SERIES[name])
            except Exception as e:
                col.error(f"{name}: {sources.clean_error(e)}")
                continue
            prev = s.iloc[-2] if len(s) > 1 else s.iloc[-1]
            col.metric(name, f"{s.iloc[-1]:,.2f}", f"{s.iloc[-1] - prev:+.2f}", delta_color="off")
            col.caption(f"as of {s.index[-1]:%Y-%m-%d}")
            fig = go.Figure(go.Scatter(x=s.index, y=s.values, line=dict(color=AMBER, width=1.5)))
            style_fig(fig, 180, showlegend=False)
            col.plotly_chart(fig, width="stretch", key=f"eco_{name}")
    st.caption("Source: FRED, Federal Reserve Bank of St. Louis. Five years of history.")


def color_moves(df: pd.DataFrame, cols: list[str]):
    """Green for gains, red for losses in the given columns."""
    def tint(v):
        if pd.isna(v) or v == 0:
            return ""
        return f"color: {GREEN}" if v > 0 else f"color: {RED}"

    return df.style.map(tint, subset=[c for c in cols if c in df.columns])


def quote_table(df: pd.DataFrame):
    st.dataframe(
        color_moves(df, ["change", "change_pct", "chg_52w_pct"]), hide_index=True, width="stretch",
        height=min(720, 38 + 35 * len(df)),
        column_config={
            "symbol": "Symbol", "name": "Name", "analyst_rating": "Analyst rating",
            "day_high": st.column_config.NumberColumn("Day high", format="%.2f"),
            "day_low": st.column_config.NumberColumn("Day low", format="%.2f"),
            "year_high": st.column_config.NumberColumn("52w high", format="%.2f"),
            "year_low": st.column_config.NumberColumn("52w low", format="%.2f"),
            "eps": st.column_config.NumberColumn("EPS", format="%.2f"),
            "change_pct": st.column_config.NumberColumn("Change %", format="%+.2f%%"),
            "chg_52w_pct": st.column_config.NumberColumn("52w %", format="%+.1f%%"),
            "last": st.column_config.NumberColumn("Last", format="%.2f"),
            "change": st.column_config.NumberColumn("Change", format="%+.2f"),
            "volume": st.column_config.NumberColumn("Volume", format="compact"),
            "market_cap": st.column_config.NumberColumn("Market cap", format="compact"),
            "pe": st.column_config.NumberColumn("P/E", format="%.1f"),
            "fwd_pe": st.column_config.NumberColumn("Fwd P/E", format="%.1f"),
        },
    )


def screen_mon():
    left, right = st.columns([2.3, 1], gap="large")
    with left:
        st.markdown("<div class='tk-name'>Watchlist</div>", unsafe_allow_html=True)
        with st.expander("Edit list"):
            syms = st.text_input("Symbols (comma separated)", ", ".join(config.WATCHLIST),
                                 help="For a permanent change, edit WATCHLIST in .env")
        watchlist_panel(tuple(s.strip().upper() for s in syms.split(",") if s.strip()))
        st.markdown(f"<div class='muted' style='margin-top:.8rem'>Click a stock to open it. {stream_badge()}</div>",
                    unsafe_allow_html=True)
    with right:
        market_panel()


@st.fragment(run_every=5)
def market_panel():
    """Index ETFs as a quick market read, Robinhood-card style."""
    rows = watch_data(("SPY", "QQQ", "DIA", "IWM"))
    names = {"SPY": "S&P 500", "QQQ": "Nasdaq 100", "DIA": "Dow Jones", "IWM": "Russell 2000"}
    for r in rows:
        r["sub"] = names.get(r["symbol"], "")
    st.markdown("<div class='box'><div class='box-title'>Market today</div>" + stock_rows(rows, compact=True)
                + "</div>", unsafe_allow_html=True)


def open_ticket(symbol: str):
    ss.ticket_symbol = symbol
    ss.pending_order = None
    ss.fn = "ORD"


def screen_omon():
    try:
        expiries = c_expiries(sym)
    except Exception:
        expiries = []
    if not expiries:
        st.info("No listed options for this symbol.")
        return
    c = st.columns([3, 2, 2, 5])
    # Default past the nearest expiries, which are often about to expire and thinly quoted.
    expiry = c[0].selectbox("Expiry", expiries, index=min(3, len(expiries) - 1), label_visibility="collapsed")
    side = c[1].segmented_control("Side", ["Calls", "Puts"], default="Calls", label_visibility="collapsed") or "Calls"
    near = c[2].toggle("Near the money", value=True, help="Only strikes within 15% of the share price")
    calls, puts = c_chain(sym, expiry)
    df = calls if side == "Calls" else puts
    last = (q or {}).get("last")
    if near and last:
        df = df[df["strike"].between(last * 0.85, last * 1.15)]
    picked = st.dataframe(
        df, hide_index=True, width="stretch", height=560, on_select="rerun", selection_mode="single-row",
        column_config={
            "contractSymbol": "contract", "lastPrice": st.column_config.NumberColumn("last", format="%.2f"),
            "bid": st.column_config.NumberColumn(format="%.2f"), "ask": st.column_config.NumberColumn(format="%.2f"),
            "openInterest": "open int.", "inTheMoney": "ITM",
            "delta": st.column_config.NumberColumn(format="%.2f"), "theta": st.column_config.NumberColumn(format="%.2f"),
            "impliedVolatility": st.column_config.NumberColumn("implied vol", format="percent"),
        },
    )
    rows = picked.selection.rows
    if rows:
        contract = df.iloc[rows[0]]
        st.button(f"Trade {contract['contractSymbol']} in the order ticket", type="primary",
                  on_click=open_ticket, args=(contract["contractSymbol"],))
    st.caption("Quotes and greeks from Alpaca when connected, otherwise Yahoo (may be delayed). Tick a row to select a contract. "
               "One contract controls 100 shares. Option orders go through Alpaca.")


def screen_alrt():
    c = st.columns([2, 2, 2, 2, 4], vertical_alignment="bottom")
    a_sym = c[0].text_input("Symbol", value=sym).strip().upper()
    direction = c[1].selectbox("When price is", ["above", "below"])
    price = c[2].number_input("Price", min_value=0.0, value=float(round((q or {}).get("last") or 0, 2)), step=0.5)
    if c[3].button("Add alert", width="stretch", disabled=not a_sym or price <= 0):
        alerts.add(a_sym, direction, price)
        st.rerun()
    items = alerts.load()
    if not items:
        st.caption("No alerts yet.")
    for i, a in enumerate(items):
        c = st.columns([6, 1])
        state = f"TRIGGERED at {a['triggered']:,.2f}" if a["triggered"] else "waiting"
        c[0].markdown(f"**{a['symbol']}** {a['direction']} {a['price']:,.2f} · "
                      f"<span style='color:{GREEN if a['triggered'] else '#888'}'>{state}</span>", unsafe_allow_html=True)
        if c[1].button("Remove", key=f"alrt_{i}"):
            alerts.save(items[:i] + items[i + 1:])
            st.rerun()
    st.caption("Alerts are checked every 15 seconds and pop up on screen. They only fire while this app is open in a browser.")


def screen_scr():
    name = st.segmented_control("Screen", list(data.SCREENS), default="Most active",
                                label_visibility="collapsed") or "Most active"
    try:
        df = c_screen(name)
    except Exception as e:
        st.error(f"Screen failed: {e}")
        return
    quote_table(df)
    st.caption("Screens are filters on public market data, not recommendations.")


SP500_MAX_AGE = 30 * 60  # refresh in the background when the saved scan is older than this


def screen_spx():
    df, age, refreshing, err = cache.get("sp500", data.sp500_scan, SP500_MAX_AGE)
    if df is None:
        if err and not refreshing:
            st.error(f"S&P 500 scan failed: {err}")
            if st.button("Try again"):
                cache.get("sp500", data.sp500_scan, 0)
                st.rerun()
            return
        st.markdown("<div class='loading'><b style='color:#fff;font-size:1.1rem'>Loading all 503 S&P 500 stocks"
                    "</b><br>The first scan takes about a minute. After that it opens instantly and refreshes "
                    "itself in the background every 30 minutes.</div>", unsafe_allow_html=True)
        wait_for_scan()
        return
    note = f"Data from {int(age // 60)} min ago" + (" · updating in the background" if refreshing else "")
    st.markdown(f"<div class='tk-name'>S&P 500</div><div class='muted'>{len(df)} stocks · {note}</div>",
                unsafe_allow_html=True)
    movers(df)
    sector_map(df)
    st.subheader("Scanner")
    views = {
        "Top today": ("chg_1d", False), "Worst today": ("chg_1d", True),
        "1M leaders": ("chg_1m", False), "3M leaders": ("chg_3m", False), "1Y leaders": ("chg_1y", False),
        "Near 52w high": ("from_high", False), "Furthest below high": ("from_high", True),
        "Oversold (RSI)": ("rsi", True), "Overbought (RSI)": ("rsi", False),
    }
    if "pe" in df.columns:
        views |= {"Lowest P/E": ("pe", True), "Lowest forward P/E": ("fwd_pe", True),
                  "Highest dividend": ("div_yield", False), "Largest": ("market_cap", False)}
    c = st.columns([7, 3, 2])
    view = c[0].segmented_control("View", list(views), default="Top today", label_visibility="collapsed") or "Top today"
    sectors = c[1].multiselect("Sector", sorted(df["sector"].unique()), placeholder="All sectors",
                               label_visibility="collapsed")
    uptrend = c[2].toggle("Uptrend only", help="Price above both its 50-day and 200-day average")
    if sectors:
        df = df[df["sector"].isin(sectors)]
    if uptrend:
        df = df[df["above_50d"] & df["above_200d"]]
    col, asc = views[view]
    pct = lambda label: st.column_config.NumberColumn(label, format="%+.1f%%")
    st.dataframe(
        color_moves(df.sort_values(col, ascending=asc, na_position="last"), ["chg_1d", "chg_1m", "chg_3m", "chg_1y"]),
        hide_index=True, width="stretch", height=640,
        column_config={
            "symbol": "Symbol", "name": "Name", "sector": "Sector", "analyst_rating": "Analyst rating",
            "market_cap": st.column_config.NumberColumn("Market cap", format="compact"),
            "pe": st.column_config.NumberColumn("P/E", format="%.1f"),
            "fwd_pe": st.column_config.NumberColumn("Fwd P/E", format="%.1f"),
            "pb": st.column_config.NumberColumn("P/B", format="%.1f"),
            "div_yield": st.column_config.NumberColumn("Div %", format="%.2f"),
            "last": st.column_config.NumberColumn("Last", format="%.2f"),
            "chg_1d": pct("1D"), "chg_1m": pct("1M"), "chg_3m": pct("3M"), "chg_1y": pct("1Y"),
            "from_high": pct("vs 52w high"),
            "rsi": st.column_config.NumberColumn("RSI 14", format="%.0f"),
            "above_50d": "> 50d avg", "above_200d": "> 200d avg",
        },
    )
    st.caption("Daily-close prices; the 1D column is as of the last scan, not live. A ranking, not a recommendation.")


@st.fragment(run_every=3)
def wait_for_scan():
    """Re-runs the page once the first background scan has finished."""
    if cache.get("sp500", data.sp500_scan, SP500_MAX_AGE)[0] is not None:
        st.rerun()


def movers(df: pd.DataFrame):
    st.subheader("Daily movers")

    def cards(rows: pd.DataFrame) -> str:
        out = []
        for r in rows.itertuples():
            color = RED if r.chg_1d < 0 else GREEN
            out.append(f"<a class='card' href='{link(r.symbol)}' target='_self'><b>{r.symbol}</b>"
                       f"<div class='n'>{htmllib.escape(r.name)}</div><div class='p'>{usd(r.last)}</div>"
                       f"<span class='pill' style='background:{color};margin-top:.4rem'>{r.chg_1d:+.2f}%</span></a>")
        return "<div class='cards'>" + "".join(out) + "</div>"

    ranked = df.dropna(subset=["chg_1d"]).sort_values("chg_1d")
    st.markdown("<div class='muted' style='margin-bottom:.5rem'>Biggest gains</div>" + cards(ranked.tail(5)[::-1])
                + "<div class='muted' style='margin:1rem 0 .5rem'>Biggest drops</div>" + cards(ranked.head(5)),
                unsafe_allow_html=True)


def sector_map(df: pd.DataFrame):
    st.subheader("Market map")
    d = df.dropna(subset=["chg_1d"]).copy()
    d["size"] = d["market_cap"].fillna(d["market_cap"].median()) if "market_cap" in d else 1
    fig = go.Figure(go.Treemap(
        ids=list(d["sector"].unique()) + list(d["symbol"]),
        labels=list(d["sector"].unique()) + list(d["symbol"]),
        parents=[""] * d["sector"].nunique() + list(d["sector"]),
        values=[0] * d["sector"].nunique() + list(d["size"]),
        branchvalues="remainder",
        marker=dict(colors=[0] * d["sector"].nunique() + list(d["chg_1d"]), cmin=-3, cmax=3, cmid=0,
                    colorscale=[[0, RED], [0.5, "#1e2124"], [1, GREEN]], line=dict(color="#000", width=1)),
        customdata=[""] * d["sector"].nunique() + [f"{v:+.2f}%" for v in d["chg_1d"]],
        texttemplate="<b>%{label}</b><br>%{customdata}", hovertemplate="%{label} %{customdata}<extra></extra>",
        tiling=dict(pad=1), pathbar=dict(visible=False), textfont=dict(color="#fff"),
    ))
    style_fig(fig, 520, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, width="stretch", config=NO_TOOLBAR)
    st.caption("Box size is market value; colour is today's move (full green at +3% or more, full red at -3%). "
               "Click a sector to zoom in, click again to zoom out.")


# ---------- backtest ----------
def screen_bt():
    c = st.columns([3, 2, 2], vertical_alignment="bottom")
    strat = c[0].selectbox("Rule", list(backtest.STRATEGIES))
    period = c[1].segmented_control("Period", ["1y", "2y", "5y", "10y"], default="5y", key="bt_period") or "5y"
    capital = c[2].number_input("Starting money ($)", min_value=100.0, value=10_000.0, step=1000.0)
    desc, params = backtest.STRATEGIES[strat]
    p = {}
    for col, (k, (label, default, lo, hi)) in zip(st.columns(len(params)), params.items()):
        p[k] = col.number_input(label, min_value=lo, max_value=hi, value=default, step=1, key=f"bt_{strat}_{k}")
    if strat == "RSI dip" and p["buy_below"] >= p["sell_above"]:
        st.warning("'Buy below' has to be lower than 'Sell above'.")
        return
    if strat == "Moving-average crossover" and p["fast"] >= p["slow"]:
        st.warning("The fast average needs fewer days than the slow one.")
        return
    df = c_history(sym, period, "1d")
    if len(df) < 60:
        st.info("Not enough price history for this symbol and period.")
        return
    r = backtest.run(df, strat, p, capital)
    s, b = r.stats, r.stats["benchmark"]
    st.markdown(f"<div class='muted' style='margin:.4rem 0 1rem'>{sym}: {desc.format(**p)} Signals are read at the "
                "close and traded at the next day's open.</div>", unsafe_allow_html=True)
    m = st.columns(6)
    m[0].metric("Final value", usd(s["final"]).replace("&#36;", "$"),
                f"{s['total_return'] - b['total_return']:+.1f} pts vs buy & hold")
    m[1].metric("Total return", f"{s['total_return']:+.1f}%", f"buy & hold {b['total_return']:+.1f}%", delta_color="off")
    m[2].metric("Yearly return", f"{s['cagr']:+.1f}%", f"buy & hold {b['cagr']:+.1f}%", delta_color="off")
    m[3].metric("Worst drop", f"{s['max_drawdown']:.1f}%", f"buy & hold {b['max_drawdown']:.1f}%", delta_color="off")
    m[4].metric("Trades", s["trades"], f"{num(s['win_rate'], '{:.0f}%')} winners" if s["win_rate"] is not None else None,
                delta_color="off")
    m[5].metric("Time invested", f"{s['exposure']:.0f}%", f"Sharpe {s['sharpe']:.2f}", delta_color="off")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=r.equity.index, y=r.equity, name="This rule", line=dict(color=ACC, width=2)))
    fig.add_trace(go.Scatter(x=r.benchmark.index, y=r.benchmark, name=f"Buy & hold {sym}",
                             line=dict(color="#8c8c8c", width=1.5)))
    style_fig(fig, 340, hovermode="x unified", legend=dict(orientation="h", y=1.08), yaxis_tickprefix="$")
    st.subheader("Account value")
    st.plotly_chart(fig, width="stretch", config=NO_TOOLBAR)

    st.subheader("Trades on the price chart")
    fig = go.Figure(go.Scatter(x=df.index, y=df.Close, name=sym, line=dict(color="#d9d9d9", width=1.3)))
    if not r.trades.empty:
        fig.add_trace(go.Scatter(x=r.trades["entry_date"], y=r.trades["entry"], mode="markers", name="Buy",
                                 marker=dict(symbol="triangle-up", size=11, color=GREEN)))
        done = r.trades[~r.trades["open"]]
        fig.add_trace(go.Scatter(x=done["exit_date"], y=done["exit"], mode="markers", name="Sell",
                                 marker=dict(symbol="triangle-down", size=11, color=RED)))
    style_fig(fig, 320, hovermode="x unified", legend=dict(orientation="h", y=1.08))
    st.plotly_chart(fig, width="stretch", config=NO_TOOLBAR)
    if not r.trades.empty:
        t = r.trades.assign(entry_date=pd.to_datetime(r.trades["entry_date"]).dt.date,
                            exit_date=pd.to_datetime(r.trades["exit_date"]).dt.date,
                            status=r.trades["open"].map({True: "still open", False: "closed"})).drop(columns="open")
        st.dataframe(color_moves(t.iloc[::-1], ["return_pct"]), hide_index=True, width="stretch", height=300,
                     column_config={"entry_date": "Bought", "entry": st.column_config.NumberColumn("Buy price", format="%.2f"),
                                    "exit_date": "Sold", "exit": st.column_config.NumberColumn("Sell price", format="%.2f"),
                                    "return_pct": st.column_config.NumberColumn("Return", format="%+.2f%%"),
                                    "days": "Days held", "status": "Status"})
    st.caption("Past results don't predict future ones. No commissions, slippage, dividends or taxes are included, "
               "and a rule tuned to fit the past usually does worse going forward.")


# ---------- ideas ----------
def chip(label: str, state: bool | None, pending: bool = False) -> str:
    if pending:
        return f"<span class='chip' style='background:#1e2124;color:#8c8c8c'>… {label}</span>"
    if state is None:
        return f"<span class='chip' style='background:#1e2124;color:#8c8c8c' title='No data'>? {label}</span>"
    color = GREEN if state else MUTED
    return f"<span class='chip' style='background:{color}22;color:{color}'>{'✓' if state else '✗'} {label}</span>"


@st.fragment(run_every=3)
def wait_for(key: str, fn, max_age: float):
    """Re-runs the page once a background job saved by cache.get() has finished."""
    if cache.get(key, fn, max_age)[0] is not None:
        st.rerun()


def screen_idea():
    scan, _, _, _ = cache.get("sp500", data.sp500_scan, SP500_MAX_AGE)
    if scan is None:
        st.markdown("<div class='loading'><b style='color:#fff'>Loading the S&P 500 scan first</b><br>"
                    "About a minute the very first time.</div>", unsafe_allow_html=True)
        wait_for_scan()
        return
    st.markdown("<div class='tk-name'>Stock ideas</div>", unsafe_allow_html=True)
    idea = st.segmented_control("List", list(ideas.IDEAS), default=next(iter(ideas.IDEAS)), key="idea_pick",
                                label_visibility="collapsed") or next(iter(ideas.IDEAS))
    desc, checks, deep = ideas.IDEAS[idea]
    s1 = ideas.stage1(scan, idea)
    top = list(s1["symbol"][: ideas.MAX_DEEP])
    key = "ideas-" + hashlib.md5((idea + ",".join(top)).encode()).hexdigest()[:10]
    job = lambda: ideas.deep_checks(top, deep)
    res, _, running, _ = cache.get(key, job, 6 * 3600) if top else ({}, None, False, None)
    st.markdown(f"<div class='muted'>{desc} {len(s1)} of {len(scan)} S&P 500 stocks pass the price checks; the top "
                f"{len(top)} by analyst rating get the deeper checks.</div>", unsafe_allow_html=True)
    if not top:
        st.caption("Nothing passes this list's checks today.")
        return

    rows = []
    for r in s1.head(ideas.MAX_DEEP).itertuples():
        found = (res or {}).get(r.symbol, {})
        chips = [chip(ideas.CHECKS[c][0], True) for c in checks]
        chips += [chip(ideas.DEEP[d][0], found.get(d), pending=res is None) for d in deep]
        passed = len(checks) + sum(1 for d in deep if found.get(d))
        color = RED if (r.chg_1d or 0) < 0 else GREEN
        rows.append((passed, f"<a class='idea' href='{link(r.symbol)}' target='_self'><div><b>{r.symbol}</b>"
                             f"<small>{htmllib.escape(r.name)} · {r.sector}</small></div><div>{''.join(chips)}</div>"
                             f"<div class='r'><b>{usd(r.last)}</b><br><span class='pill' style='background:{color}'>"
                             f"{r.chg_1d:+.2f}%</span><br><span class='score'>{passed} of {len(checks) + len(deep)} checks"
                             f"</span></div></a>"))
    rows.sort(key=lambda x: -x[0])
    st.markdown("<div>" + "".join(h for _, h in rows) + "</div>", unsafe_allow_html=True)
    if res is None and running:
        st.caption("Running the deeper checks in the background (about 2 seconds per stock)…")
        wait_for(key, job, 6 * 3600)
    if len(s1) > len(top):
        with st.expander(f"{len(s1) - len(top)} more passed the price checks"):
            st.markdown(" · ".join(f"<a href='{link(s)}' target='_self' style='color:var(--acc)'>{s}</a>"
                                   for s in s1["symbol"][len(top):]), unsafe_allow_html=True)
    with st.expander("What each check means"):
        for c in checks:
            st.markdown(f"**{ideas.CHECKS[c][0]}**: {ideas.CHECKS[c][1]}")
        for d in deep:
            st.markdown(f"**{ideas.DEEP[d][0]}**: {ideas.DEEP[d][1]}")
    st.caption("These are filters on public data, not recommendations. ? means the data source had nothing for "
               "that stock. Price checks use the S&P 500 scan (refreshed every 30 minutes).")


# ---------- earnings calendar ----------
def my_symbols() -> tuple[list[str], list[str]]:
    """(held, watchlist-only) stock symbols."""
    held = c_held()
    return held, [s for s in config.WATCHLIST if s not in held]


def when_label(d) -> str:
    days = (d - pd.Timestamp.now(tz="America/New_York").date()).days
    return "Today" if days == 0 else "Tomorrow" if days == 1 else f"In {days} days"


def screen_cal():
    if needs_key("FINNHUB_API_KEY", config.FINNHUB_API_KEY, "finnhub.io"):
        return
    held, watch = my_symbols()
    up = c_upcoming(tuple(held + watch))
    st.markdown("<div class='tk-name'>Earnings calendar</div>"
                f"<div class='muted'>Next reports for your {len(held)} holdings and {len(watch)} watchlist stocks, "
                "next 45 days. Funds like SPY don't report earnings.</div>", unsafe_allow_html=True)
    if up.empty:
        st.markdown("<div class='loading' style='margin-top:1rem'>None of your stocks report in the next 45 days."
                    "</div>", unsafe_allow_html=True)
        return
    hours = {"bmo": "Before the open", "amc": "After the close", "dmh": "During market hours"}
    rows = []
    for r in up.itertuples():
        try:
            s = c_surprises(r.symbol).head(4)
            record = f"Beat {int((s['surprisePercent'] > 0).sum())} of last {len(s)}" if not s.empty else "No history"
        except Exception:
            record = "-"
        soon = when_label(r.date) in ("Today", "Tomorrow")
        tag = "Holding" if r.symbol in held else "Watchlist"
        rows.append(
            f"<div class='cal{' soon' if soon else ''}'><div><b>{r.date:%a, %b %d}</b><small>{when_label(r.date)}</small>"
            f"</div><div><a href='{link(r.symbol)}' target='_self'>{r.symbol}</a><small>{tag} · "
            f"{hours.get(r.hour, 'Time not announced')}</small></div>"
            f"<div><small>EPS estimate</small>{usd(r.epsEstimate)}</div>"
            f"<div><small>Revenue estimate</small>{big(r.revenueEstimate)}</div>"
            f"<div><small>Track record</small>{record}</div></div>")
    st.markdown("<div style='margin-top:1rem'>" + "".join(rows) + "</div>", unsafe_allow_html=True)
    st.caption("A reminder pops up the day before and the day of each report while the app is open.")


@st.fragment(run_every=600)
def earnings_reminders():
    if not config.FINNHUB_API_KEY:
        return
    held, watch = my_symbols()
    up = c_upcoming(tuple(held + watch))
    shown = ss.setdefault("reminded", set())
    hours = {"bmo": "before the open", "amc": "after the close"}
    for r in up.itertuples() if not up.empty else []:
        label = when_label(r.date)
        if label in ("Today", "Tomorrow") and (r.symbol, r.date) not in shown:
            shown.add((r.symbol, r.date))
            st.toast(f"{r.symbol} reports earnings {label.lower()} {hours.get(r.hour, '')} "
                     f"(EPS estimate {num(r.epsEstimate)})", icon="📅")


# ---------- prediction markets ----------
def pred_card(e: dict, n: int = 5) -> str:
    bars = "".join(
        f"<div class='bar'><span>{htmllib.escape(str(label))[:60]}</span><div class='track'><div class='fill' "
        f"style='width:{p * 100:.0f}%;background:{GREEN if i == 0 else '#5c5f63'}'></div></div>"
        f"<span class='r'>{p * 100:.0f}%</span></div>" for i, (label, p) in enumerate(e["outcomes"][:n]))
    more = f"<small class='muted'>+{len(e['outcomes']) - n} more outcomes</small>" if len(e["outcomes"]) > n else ""
    sub = f" · {htmllib.escape(e['subtitle'])}" if e["subtitle"] else ""
    return (f"<div class='pred'><a href='{e['url']}' target='_blank'>{htmllib.escape(e['title'])}</a>"
            f"<div class='muted' style='font-size:.78rem;margin:.15rem 0 .5rem'>{e['source']}{sub} · volume "
            f"{big(e['volume'])}</div>{bars}{more}</div>")


def prediction_notice(errors: dict) -> str:
    return ("Kalshi and Polymarket can't be reached from this computer: the connection is cut during the secure "
            "handshake, which is what a network filter does. Your network (often a company network or security "
            "software) appears to block these sites. On a network that allows kalshi.com and polymarket.com this "
            "fills in on its own.") if errors and all("handshake" in v for v in errors.values()) else \
        "; ".join(f"{k}: {v}" for k, v in errors.items())


def screen_pred():
    events, errors = c_predictions()
    st.markdown("<div class='tk-name'>Prediction markets</div><div class='muted'>What traders are paying for "
                "each outcome, read as the market's odds. From Kalshi and Polymarket, refreshed every 10 minutes."
                "</div>", unsafe_allow_html=True)
    if errors:
        (st.info if not events else st.warning)(prediction_notice(errors))
    if not events:
        return
    c = st.columns([5, 3], vertical_alignment="center")
    topic = c[0].segmented_control("Topic", [*predictions.TOPICS, "All"], default="Fed & rates", key="pred_topic",
                                   label_visibility="collapsed") or "All"
    query = c[1].text_input("Search markets", placeholder="Search markets, e.g. tariffs", label_visibility="collapsed")
    found = predictions.matching(events, None if topic == "All" else topic, query)[:30]
    if not found:
        st.caption("No open markets match.")
        return
    cols = st.columns(2, gap="medium")
    for i, e in enumerate(found):
        cols[i % 2].markdown(pred_card(e), unsafe_allow_html=True)


# ---------- morning brief ----------
def brief_context() -> str:
    held, watch = my_symbols()
    syms = held + watch
    ctx: dict = {"date": pd.Timestamp.now(tz="America/New_York").strftime("%A %B %d, %Y %H:%M ET")}
    market = c_quotes(("SPY", "QQQ", "DIA", "IWM"))
    ctx["market_etfs"] = market[["symbol", "last", "change_pct"]].round(2).to_dict("records")
    if config.FRED_API_KEY:
        try:
            ctx["economy"] = {n: round(float(c_fred(sources.FRED_SERIES[n]).iloc[-1]), 2)
                              for n in ("Fed funds rate", "10-year Treasury", "VIX", "CPI inflation (YoY %)")}
        except Exception:
            pass
    ctx["holdings"] = {}
    for name, b in brokers.items():
        try:
            ctx["holdings"][name] = b.positions()
        except Exception:
            pass
    q_all = c_quotes(tuple(syms)) if syms else pd.DataFrame()
    ctx["moves_today"] = (q_all[["symbol", "last", "change_pct", "volume"]].round(2).to_dict("records")
                          if not q_all.empty else [])
    ctx["headlines"] = {s: [{k: n[k] for k in ("title", "publisher", "published", "url")} for n in c_news(s)[:3]]
                        for s in syms}
    if config.FINNHUB_API_KEY:
        up = c_upcoming(tuple(syms))
        if not up.empty:
            soon = up[pd.to_datetime(up["date"]) <= pd.Timestamp.now() + pd.Timedelta(days=7)]
            ctx["earnings_next_7_days"] = soon[["symbol", "date", "hour", "epsEstimate"]].astype(str).to_dict("records")
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
        trades = []
        for s in syms:
            try:
                t = c_insiders(s)
                t = t[t["transactionCode"].isin(["P", "S"]) & (pd.to_datetime(t["transactionDate"]) > cutoff)]
                trades += t[["symbol", "name", "transactionCode", "change", "transactionPrice", "transactionDate"]] \
                    .head(5).to_dict("records")
            except Exception:
                pass
        ctx["insider_open_market_trades_30d"] = trades
    events, _ = c_predictions()
    if events:
        ctx["prediction_market_odds"] = [{"title": e["title"], "outcomes": [(o, round(p, 3)) for o, p in e["outcomes"][:4]]}
                                         for e in predictions.matching(events, "Fed & rates")[:3]]
    return json.dumps(ctx, default=str)


BRIEF_PROMPT = """Write my morning brief for today from the data in <context>. Use these sections, skipping any \
that have nothing worth saying: **Market** (index ETFs, rates, VIX, Fed odds), **My holdings**, **Watchlist \
movers**, **Earnings this week**, **Insider activity**, **Headlines worth reading** (as markdown links), \
**What to watch today**. Under 400 words, bullet points, concrete numbers. Use only facts that appear in \
<context> (including its headlines); do not add figures from memory, and say when data is missing. \
Flag things to look into rather than telling me what to buy or sell."""


def screen_brf():
    if not config.AI_PROVIDER:
        st.info("Add GEMINI_API_KEY or ANTHROPIC_API_KEY to .env to use the morning brief.")
        return
    from terminal import ai

    today = pd.Timestamp.now(tz="America/New_York").date()
    path = cache.DIR / f"brief-{today}.md"
    c = st.columns([6, 1], vertical_alignment="center")
    c[0].markdown(f"<div class='tk-name'>Morning brief</div><div class='muted'>{today:%A, %B %d} · written by "
                  f"{config.AI_PROVIDER} from your holdings, watchlist and today's data</div>", unsafe_allow_html=True)
    rewrite = c[1].button("Rewrite", width="stretch")
    st.divider()
    if path.exists() and not rewrite:
        st.markdown(path.read_text(encoding="utf-8").replace("$", "\\$"))
        st.caption(f"Written at {pd.Timestamp(path.stat().st_mtime, unit='s', tz='UTC').tz_convert('America/New_York'):%H:%M} ET. "
                   "A new one is written the first time you open this screen each day.")
        return
    with st.spinner("Gathering prices, news, earnings and insider trades for your stocks…"):
        ctx = brief_context()
    messages = [{"role": "user", "content": f"<context>{ctx}</context>\n\n{BRIEF_PROMPT}"}]
    try:
        text = st.write_stream(t.replace("$", "\\$") for t in ai.stream_answer(messages))
    except Exception as e:
        st.error(ai.error_text(e))
        return
    cache.DIR.mkdir(exist_ok=True)
    path.write_text(text.replace("\\$", "$"), encoding="utf-8")


# Raw broker status (Alpaca snake_case, IBKR CamelCase, compared lower-case, no "_") ->
# (plain label, state). "open" orders can still be canceled.
ORDER_STATUS = {
    "pendingsubmit": ("Sending to IBKR", "open"), "apipending": ("Sending to IBKR", "open"),
    "presubmitted": ("Waiting for market open", "open"), "submitted": ("Working", "open"),
    "pendingcancel": ("Canceling", "open"), "pendingnew": ("Sending to Alpaca", "open"),
    "new": ("Working", "open"), "accepted": ("Accepted", "open"), "held": ("Waiting to trigger", "open"),
    "acceptedforbidding": ("Accepted", "open"), "partiallyfilled": ("Partly filled", "open"),
    "pendingreplace": ("Updating", "open"), "calculated": ("Working", "open"),
    "filled": ("Filled", "done"), "doneforday": ("Done for the day", "done"),
    "cancelled": ("Canceled", "closed"), "canceled": ("Canceled", "closed"), "apicancelled": ("Canceled", "closed"),
    "expired": ("Expired", "closed"), "rejected": ("Rejected", "closed"), "inactive": ("Not active", "closed"),
    "replaced": ("Replaced", "closed"), "stopped": ("Stopped", "closed"), "suspended": ("Suspended", "closed"),
}


def order_status(o: dict) -> tuple[str, str]:
    raw = (o.get("status") or "").lower().replace("_", "")
    return ORDER_STATUS.get(raw, ((o.get("status") or "Unknown").replace("_", " ").capitalize(), "open"))


def order_row(o: dict) -> str:
    status, state = order_status(o)
    color = GREEN if state == "done" else MUTED if state == "closed" else AMBER
    when = pd.Timestamp(o["submitted"]).strftime("%b %d, %H:%M") if o.get("submitted") else ""
    price = f" @ {usd(o['limit_price'])}" if o.get("limit_price") else ""
    return (f"<div class='line' style='border-bottom:1px solid {LINE};padding:.75rem 0'>"
            f"<div><b>{o['symbol']}</b> <span class='muted'>{(o.get('type') or '').title()} "
            f"{(o.get('side') or '').title()}{price}</span><br><small class='muted'>{when}</small></div>"
            f"<div class='r'>{(o.get('qty') or 0):g} {'share' if o.get('qty') == 1 else 'shares'}<br>"
            f"<small style='color:{color}'>{status}</small></div></div>")


def broker_notices():
    for name, err in broker_errors.items():
        st.warning(f"{name} not connected: {err}")
    if not brokers and not broker_errors:
        st.info("No broker configured yet. Copy .env.example to .env, add your Alpaca keys "
                "(and set IBKR_ENABLED=true for Interactive Brokers), then restart the app.")
    if st.button("Reconnect brokers"):
        c_brokers.clear()
        st.rerun()


def screen_port():
    if not brokers:
        broker_notices()
        return
    names = list(brokers)
    left, right = st.columns([2.3, 1], gap="large")
    with left:
        bname = (st.segmented_control("Account", names, default=names[0], label_visibility="collapsed")
                 if len(names) > 1 else names[0]) or names[0]
        b = brokers[bname]
        try:
            a, positions = b.account(), b.positions()
        except Exception as e:
            st.error(f"{bname}: {e}")
            return
        chart_box = st.container()
        rng = st.segmented_control("Range", ["1D", "1W", "1M", "3M", "1Y"], default="1D", key="port_range",
                                   label_visibility="collapsed") or "1D"
        with chart_box:
            try:
                hist = c_port_history(bname, rng)
            except Exception:
                hist = pd.Series(dtype=float)
            start = hist.iloc[0] if len(hist) else a["equity"]
            move = a["equity"] - start
            color = RED if move < 0 else GREEN
            label = {"1D": "Today", "1W": "Past week", "1M": "Past month", "3M": "Past 3 months", "1Y": "Past year"}[rng]
            st.markdown(
                f"<div class='muted'>{bname} · investing</div><div class='tk-px'>{usd(a['equity'])}</div>"
                f"<div class='tk-chg' style='color:{color}'>{usd(move, sign=True)} "
                f"({num(move / start * 100 if start else 0, '{:+.2f}%')})<small>{label}</small></div>",
                unsafe_allow_html=True)
            if len(hist) > 1:
                line_chart(hist, 280, color, start if rng == "1D" else None)
            else:
                st.markdown("<div class='loading'>No account history for this range yet.</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='line' style='border-top:1px solid {LINE};border-bottom:1px solid {LINE};padding:.9rem 0'>"
            f"<b>Buying power</b><b>{usd(a['buying_power'])}</b></div>"
            f"<div class='line'><span class='muted'>Cash</span><span>{usd(a['cash'])}</span></div>",
            unsafe_allow_html=True)
        st.subheader("Positions")
        if not positions:
            st.caption("No open positions yet. Open a stock and use the order card to buy.")
        else:
            syms = tuple(p["symbol"] for p in positions if not OrderRequest(p["symbol"], "buy", 1).is_option)
            sparks = c_sparks(syms) if syms else {}
            rows = []
            for p in positions:
                pl, cost = p.get("unrealized_pl") or 0, (p.get("avg_cost") or 0) * (p.get("qty") or 0)
                rows.append({
                    "symbol": p["symbol"], "last": p.get("price"), "spark": sparks.get(p["symbol"]),
                    "change_pct": pl / abs(cost) * 100 if cost else None,
                    "sub": f"{p['qty']:g} shares · avg {usd(p.get('avg_cost'))}",
                    "extra": f"{usd(p.get('market_value'))}<small style='color:{RED if pl < 0 else GREEN}'>"
                             f"{usd(pl, sign=True)} total return</small>",
                })
            st.markdown(stock_rows(rows), unsafe_allow_html=True)
            st.caption("The pill on each position is its total return since you bought it.")
        portfolio_analytics(positions, hist, rng)
        for name, err in broker_errors.items():
            st.warning(f"{name} not connected: {err}")
    with right:
        st.markdown("<div class='box-title'>Watchlist</div>", unsafe_allow_html=True)
        watchlist_panel(tuple(config.WATCHLIST), compact=True)


PORT_SPY = {"1D": ("1d", "5m"), "1W": ("5d", "15m"), "1M": ("1mo", "1d"), "3M": ("3mo", "1d"), "1Y": ("1y", "1d")}


def portfolio_analytics(positions: list[dict], hist: pd.Series, rng: str):
    st.subheader("Analytics")
    # Performance against the S&P 500 over the same range
    spy = c_history("SPY", *PORT_SPY[rng]).Close
    if len(hist) > 1 and len(spy) > 1:
        spy = spy[spy.index >= hist.index[0]] if rng != "1D" else spy
        mine, mkt = (hist / hist.iloc[0] - 1) * 100, (spy / spy.iloc[0] - 1) * 100
        fig = go.Figure([go.Scatter(x=mine.index, y=mine, name="Your account", line=dict(color=ACC, width=2),
                                    hovertemplate="You %{y:+.2f}%<extra></extra>"),
                         go.Scatter(x=mkt.index, y=mkt, name="S&P 500 (SPY)", line=dict(color="#8c8c8c", width=1.5),
                                    hovertemplate="S&P 500 %{y:+.2f}%<extra></extra>")])
        fig.add_hline(y=0, line=dict(color="#4a4d52", width=1, dash="dot"))
        style_fig(fig, 260, hovermode="x unified", legend=dict(orientation="h", y=1.12), yaxis_ticksuffix="%")
        skip_closed_hours(fig, "1D" if rng == "1D" else "1W" if rng == "1W" else "1Y")
        st.markdown(f"<div class='muted'>Your account <b style='color:#fff'>{mine.iloc[-1]:+.2f}%</b> vs the S&P 500 "
                    f"<b style='color:#fff'>{mkt.iloc[-1]:+.2f}%</b> over this range</div>", unsafe_allow_html=True)
        st.plotly_chart(fig, width="stretch", config=NO_TOOLBAR)
    if not positions:
        st.caption("Allocation and profit by position appear once you hold something.")
        return
    c = st.columns(2, gap="large")
    # Allocation by sector
    alloc: dict[str, float] = {}
    for p in positions:
        if OrderRequest(p["symbol"], "buy", 1).is_option:
            sector = "Options"
        else:
            try:
                info = c_info(p["symbol"])
                sector = info.get("sector") or ("Funds" if info.get("quoteType") == "ETF" else "Other")
            except Exception:
                sector = "Other"
        alloc[sector] = alloc.get(sector, 0) + abs(p.get("market_value") or 0)
    fig = go.Figure(go.Pie(labels=list(alloc), values=list(alloc.values()), hole=0.62, sort=True,
                           textinfo="percent", hovertemplate="%{label}: $%{value:,.0f} (%{percent})<extra></extra>"))
    style_fig(fig, 300, legend=dict(orientation="v", x=1, y=0.5))
    with c[0]:
        st.markdown("<div class='box-title'>Allocation by sector</div>", unsafe_allow_html=True)
        st.plotly_chart(fig, width="stretch", config=NO_TOOLBAR)
    # Profit or loss per position
    pl = sorted(((p["symbol"], p.get("unrealized_pl") or 0) for p in positions), key=lambda x: x[1])
    fig = go.Figure(go.Bar(x=[v for _, v in pl], y=[s for s, _ in pl], orientation="h",
                           marker_color=[GREEN if v >= 0 else RED for _, v in pl],
                           hovertemplate="%{y}: $%{x:+,.2f}<extra></extra>"))
    style_fig(fig, max(220, 40 * len(pl)), xaxis_tickprefix="$")
    with c[1]:
        st.markdown("<div class='box-title'>Profit or loss by position</div>", unsafe_allow_html=True)
        st.plotly_chart(fig, width="stretch", config=NO_TOOLBAR)


def screen_ord():
    broker_notices()
    if not brokers:
        return
    ticket, book = st.columns([1, 1.6], gap="large")
    with ticket:
        with st.container(border=True):
            order_ticket(symbol_input=True)
    with book:
        st.markdown("<div class='tk-name' style='font-size:1.5rem'>Orders</div>", unsafe_allow_html=True)
        orders_panel()


@st.fragment(run_every=3)
def orders_panel():
    """Order list; re-asks each broker for statuses every few seconds."""
    for name, b in brokers.items():
        try:
            orders = b.orders()
        except Exception as e:
            st.error(f"{name}: {e}")
            continue
        if len(brokers) > 1:
            st.caption(name)
        if not orders:
            st.caption("No orders yet.")
            continue
        st.markdown("<div>" + "".join(order_row(o) for o in orders[:25]) + "</div>", unsafe_allow_html=True)
        open_ = [o for o in orders if order_status(o)[1] == "open"]
        if open_:
            pick = st.selectbox(f"Cancel an open {name} order", open_, key=f"cx_{name}",
                                format_func=lambda o: f"{o['side'].upper()} {o['qty']:g} {o['symbol']} "
                                                      f"({order_status(o)[0]})")
            if st.button("Cancel order", key=f"cxb_{name}"):
                try:
                    b.cancel_order(pick["id"])
                    st.success("Cancel request sent.")
                except Exception as e:
                    st.error(f"Cancel failed: {e}")


def ai_context() -> str:
    ctx: dict = {"ticker": sym, "quote": q}
    i = c_info(sym)
    ctx["fundamentals"] = {k: i.get(k) for k in (
        "longName", "sector", "industry", "marketCap", "trailingPE", "forwardPE", "priceToSalesTrailing12Months",
        "revenueGrowth", "earningsGrowth", "grossMargins", "operatingMargins", "profitMargins", "returnOnEquity",
        "freeCashflow", "debtToEquity", "beta", "recommendationKey", "targetMeanPrice", "numberOfAnalystOpinions")}
    ctx["headlines"] = [{k: n[k] for k in ("title", "publisher", "published")} for n in c_news(sym)[:10]]
    # Extra sources; each is optional, so a missing key or failed call just leaves that part out.
    def add(key, fn_):
        try:
            ctx[key] = fn_()
        except Exception:
            pass

    if config.FMP_API_KEY:
        add("valuation_models", lambda: {
            "dcf": c_fmp("discounted-cash-flow", sym), "scores": c_fmp("financial-scores", sym),
            "rating": c_fmp("ratings-snapshot", sym), "price_target": c_fmp("price-target-consensus", sym)})
    if config.FINNHUB_API_KEY:
        add("earnings_vs_estimates", lambda: c_surprises(sym).to_dict("records"))
        add("insider_open_market_trades", lambda: (lambda d: d[d["transactionCode"].isin(["P", "S"])].head(15)[
            ["transactionDate", "name", "transactionCode", "change", "transactionPrice"]].to_dict("records"))(c_insiders(sym)))
    add("recent_sec_filings", lambda: (lambda f: f[f["form"].isin(["10-K", "10-Q", "8-K"])].head(12)[
        ["filed", "form", "items", "url"]].to_dict("records"))(c_filings(sym)))
    if config.FRED_API_KEY:
        add("economy", lambda: {name: round(float(c_fred(sid).iloc[-1]), 2) for name, sid in sources.FRED_SERIES.items()})
    add("prediction_market_odds", lambda: [
        {"title": e["title"], "source": e["source"], "outcomes": [(o, round(p, 3)) for o, p in e["outcomes"][:4]]}
        for e in predictions.matching(c_predictions()[0], "Fed & rates")[:3]
        + predictions.matching(c_predictions()[0], None, company or sym)[:3]])
    ctx["holdings"] = {}
    for name, b in brokers.items():
        try:
            ctx["holdings"][name] = {"account": b.account(), "positions": b.positions()}
        except Exception:
            pass
    return json.dumps(ctx, default=str)


def screen_ai():
    if not config.AI_PROVIDER:
        st.info("Add GEMINI_API_KEY or ANTHROPIC_API_KEY to .env to use the research panel, or skip the key "
                "and connect Claude Code / Claude Desktop to this app's data instead (see README).")
        return
    from terminal import ai

    c = st.columns([8, 1])
    c[0].caption(f"{config.AI_PROVIDER} sees the data on screen for {sym} plus your holdings, and can search "
                 "the web. It cannot place orders.")
    if c[1].button("Clear"):
        ss.chat, ss.chat_api = [], []
        st.rerun()
    for role, text in ss.chat:
        st.chat_message(role).markdown(text)
    prompt = st.chat_input(f"Ask about {sym}, your portfolio, or the market")
    if not prompt:
        return
    st.chat_message("user").markdown(prompt)
    ss.chat.append(("user", prompt))
    turn_start = len(ss.chat_api)
    ss.chat_api.append({"role": "user", "content": f"<context>{ai_context()}</context>\n\n{prompt}"})
    with st.chat_message("assistant"):
        try:
            # Escape "$" so prices are not swallowed as LaTeX math by the markdown renderer.
            text = st.write_stream(t.replace("$", "\\$") for t in ai.stream_answer(ss.chat_api))
            ss.chat.append(("assistant", text))
        except Exception as e:
            ss.chat.pop()
            del ss.chat_api[turn_start:]
            st.error(ai.error_text(e))


def screen_help():
    st.subheader("Keyboard shortcuts")
    st.markdown("In the search box, type a ticker, a screen code, or both, then press Enter. "
                "Examples: `NVDA`, `GP`, `MSFT FA`, `PORT`.")
    st.dataframe(pd.DataFrame([(c, g, s) for g, items in NAV.items() for c, s in items.items()],
                              columns=["Code", "Section", "Screen"]), hide_index=True, width=520, height=668)
    st.caption(f"Mode: {config.MODE_LABEL}. Change TRADING_MODE in .env and restart to switch. "
               "Market data comes from Yahoo Finance and may be delayed.")


{"DES": screen_des, "GP": screen_gp, "FA": screen_fa, "N": screen_news, "ANR": screen_anr, "VAL": screen_val,
 "ERN": screen_ern, "SEC": screen_sec, "ECO": screen_eco, "MON": screen_mon,
 "SCR": screen_scr, "SPX": screen_spx, "OMON": screen_omon, "ALRT": screen_alrt, "PORT": screen_port, "ORD": screen_ord,
 "AI": screen_ai, "HELP": screen_help, "BT": screen_bt, "IDEA": screen_idea, "CAL": screen_cal, "PRED": screen_pred,
 "BRF": screen_brf}[fn]()
earnings_reminders()  # last, so its first (slower) data fetch never holds up the screen
