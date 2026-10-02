"""Extra data sources: SEC EDGAR, FRED, Finnhub, Financial Modeling Prep."""
from __future__ import annotations

import datetime as dt
from functools import lru_cache

import pandas as pd
import requests

from . import config

TIMEOUT = 20


def clean_error(e: Exception) -> str:
    """Error text with API keys removed (request errors include the full URL)."""
    msg = str(e)
    for key in (config.FINNHUB_API_KEY, config.FMP_API_KEY, config.FRED_API_KEY):
        if key:
            msg = msg.replace(key, "***")
    return msg


def _get(url: str, **kw) -> requests.Response:
    r = requests.get(url, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r


# ---------- SEC EDGAR (no key; SEC requires a contact email in the User-Agent) ----------
def _sec_headers() -> dict:
    return {"User-Agent": f"TradingTerminal {config.SEC_CONTACT_EMAIL or 'admin@example.com'}"}


@lru_cache(maxsize=1)
def _cik_map() -> dict[str, int]:
    rows = _get("https://www.sec.gov/files/company_tickers.json", headers=_sec_headers()).json()
    return {v["ticker"]: v["cik_str"] for v in rows.values()}


def sec_filings(symbol: str) -> pd.DataFrame:
    """Recent filings: date, form, description, 8-K item codes, link to the document."""
    cik = _cik_map().get(symbol.upper().replace(".", "-"))
    if cik is None:
        return pd.DataFrame()
    recent = _get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers=_sec_headers()).json()["filings"]["recent"]
    df = pd.DataFrame(recent)
    df["url"] = [
        f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{doc}"
        for acc, doc in zip(df["accessionNumber"], df["primaryDocument"])
    ]
    return df.rename(columns={"filingDate": "filed", "reportDate": "period", "primaryDocDescription": "description"})[
        ["filed", "form", "description", "period", "items", "url"]
    ]


# ---------- FRED (free key) ----------
FRED_SERIES = {
    "Fed funds rate": "DFF",
    "2-year Treasury": "DGS2",
    "10-year Treasury": "DGS10",
    "10y minus 2y spread": "T10Y2Y",
    "30-year mortgage": "MORTGAGE30US",
    "CPI inflation (YoY %)": "CPIAUCSL",
    "Unemployment rate": "UNRATE",
    "Real GDP growth (QoQ ann. %)": "A191RL1Q225SBEA",
    "VIX": "VIXCLS",
    "High-yield credit spread": "BAMLH0A0HYM2",
}


def fred_series(series_id: str, years: int = 5) -> pd.Series:
    start = dt.date.today() - dt.timedelta(days=365 * years + 400)
    params = {"series_id": series_id, "api_key": config.FRED_API_KEY, "file_type": "json", "observation_start": str(start)}
    if series_id == "CPIAUCSL":
        params["units"] = "pc1"  # percent change from a year ago
    obs = _get("https://api.stlouisfed.org/fred/series/observations", params=params).json()["observations"]
    s = pd.Series({pd.Timestamp(o["date"]): o["value"] for o in obs})
    return pd.to_numeric(s, errors="coerce").dropna()


# ---------- Finnhub (free key) ----------
def _finnhub(path: str, **params):
    return _get(f"https://finnhub.io/api/v1{path}", params={**params, "token": config.FINNHUB_API_KEY}).json()


def earnings_calendar(days: int = 14) -> pd.DataFrame:
    today = dt.date.today()
    rows = _finnhub("/calendar/earnings", **{"from": str(today), "to": str(today + dt.timedelta(days=days))})
    df = pd.DataFrame(rows.get("earningsCalendar", []))
    return df.sort_values(["date", "symbol"]) if not df.empty else df


def upcoming_earnings(symbols: list[str], days: int = 45) -> pd.DataFrame:
    """Next scheduled report per symbol (asked one symbol at a time: the all-market calendar is truncated)."""
    today = dt.date.today()
    rows = []
    for s in symbols:
        try:
            got = _finnhub("/calendar/earnings", symbol=s, **{"from": str(today), "to": str(today + dt.timedelta(days=days))})
        except Exception:
            continue
        rows += got.get("earningsCalendar", [])
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.drop_duplicates(["symbol", "date"]).sort_values(["date", "symbol"])
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def earnings_surprises(symbol: str) -> pd.DataFrame:
    return pd.DataFrame(_finnhub("/stock/earnings", symbol=symbol.upper()))


def insider_transactions(symbol: str) -> pd.DataFrame:
    return pd.DataFrame(_finnhub("/stock/insider-transactions", symbol=symbol.upper()).get("data", []))


# ---------- Financial Modeling Prep (free key) ----------
FMP_VIEWS = {
    "Fair value (DCF)": "discounted-cash-flow",
    "Rating": "ratings-snapshot",
    "Financial health scores": "financial-scores",
    "Price target consensus": "price-target-consensus",
    "Ratios (ttm)": "ratios-ttm",
    "Key metrics (ttm)": "key-metrics-ttm",
}


def fmp(endpoint: str, symbol: str) -> dict:
    """First record of an FMP per-symbol endpoint, as a flat dict."""
    rows = _get(
        f"https://financialmodelingprep.com/stable/{endpoint}",
        params={"symbol": symbol.upper(), "apikey": config.FMP_API_KEY},
    ).json()
    if isinstance(rows, dict):
        if "Error Message" in rows:
            raise RuntimeError(rows["Error Message"])
        return rows
    return rows[0] if rows else {}
