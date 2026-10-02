"""Read-only MCP server so Claude Code / Claude Desktop can query the terminal's data.

Nothing here can place, change or cancel an order.
Register with:  claude mcp add trading-terminal -- <path>\\.venv\\Scripts\\python.exe <path>\\mcp_server.py
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from terminal import config, data
from terminal.brokers import connect_all

mcp = MCPServer("trading-terminal")


@mcp.tool()
def get_quote(symbol: str) -> dict:
    """Latest price, day range, volume, market cap and 52-week range for a ticker."""
    return data.quote(symbol.upper())


@mcp.tool()
def get_fundamentals(symbol: str) -> dict:
    """Company profile, valuation ratios, margins, growth and analyst targets."""
    return data.info(symbol.upper())


@mcp.tool()
def get_news(symbol: str, limit: int = 15) -> list[dict]:
    """Recent news headlines for a ticker."""
    return data.news(symbol.upper(), limit)


@mcp.tool()
def get_price_history(symbol: str, period: str = "6mo", interval: str = "1d") -> str:
    """OHLCV price history as CSV. period: 1d,5d,1mo,3mo,6mo,1y,2y,5y,max. interval: 1m,5m,15m,1h,1d,1wk,1mo."""
    return data.history(symbol.upper(), period, interval).round(4).to_csv()


@mcp.tool()
def run_screen(name: str) -> list[dict]:
    """Run a stock screen. Names: Most active, Day gainers, Day losers, Undervalued growth,
    Undervalued large caps, Growth technology, Aggressive small caps, Small cap gainers."""
    return data.screen(name).to_dict("records")


@mcp.tool()
def get_portfolio() -> dict:
    """Account balances, positions and recent orders at every connected broker (read-only)."""
    brokers, errors = connect_all()
    out: dict = {"mode": config.MODE_LABEL, "errors": errors}
    for name, b in brokers.items():
        out[name] = {
            "account": b.account(),
            "positions": b.positions(),
            "orders": [{**o, "submitted": str(o["submitted"])} for o in b.orders()],
        }
    return out


if __name__ == "__main__":
    mcp.run()
