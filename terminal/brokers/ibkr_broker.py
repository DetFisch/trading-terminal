"""Interactive Brokers via ib_async. Needs TWS or IB Gateway running locally.

ib_async is asyncio-based and Streamlit reruns the script on arbitrary threads, so
the IB connection lives on its own event-loop thread and every call hops onto it.
"""
from __future__ import annotations

import asyncio
import threading

from ib_async import IB, LimitOrder, MarketOrder, Stock, StopOrder

from .base import Broker, OrderRequest

ACTIVE = {"PendingSubmit", "ApiPending", "PreSubmitted", "Submitted"}


class IBKRBroker(Broker):
    name = "Interactive Brokers"

    def __init__(self, host: str, port: int, client_id: int):
        self.host, self.port, self.client_id = host, port, client_id
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        self.ib: IB | None = None
        self._run(self._connect())

    def _run(self, coro, timeout: float = 20):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)

    async def _connect(self):
        self.ib = IB()
        await self.ib.connectAsync(self.host, self.port, clientId=self.client_id, timeout=8)

    async def _ensure(self):
        if self.ib is None or not self.ib.isConnected():
            await self._connect()

    def account(self) -> dict:
        async def go():
            await self._ensure()
            vals = {
                v.tag: v.value
                for v in self.ib.accountValues()
                if v.currency in ("USD", "BASE") and v.tag in ("NetLiquidation", "TotalCashValue", "BuyingPower")
            }
            return {
                "equity": float(vals.get("NetLiquidation", 0) or 0),
                "cash": float(vals.get("TotalCashValue", 0) or 0),
                "buying_power": float(vals.get("BuyingPower", 0) or 0),
                "currency": "USD",
            }

        return self._run(go())

    def positions(self) -> list[dict]:
        async def go():
            await self._ensure()
            return [
                {
                    "symbol": p.contract.symbol,
                    "qty": p.position,
                    "avg_cost": p.averageCost,
                    "price": p.marketPrice,
                    "market_value": p.marketValue,
                    "unrealized_pl": p.unrealizedPNL,
                }
                for p in self.ib.portfolio()
            ]

        return self._run(go())

    def orders(self) -> list[dict]:
        async def go():
            await self._ensure()
            await self.ib.reqAllOpenOrdersAsync()
            return [
                {
                    "id": str(t.order.orderId),
                    "symbol": t.contract.symbol,
                    "side": t.order.action.lower(),
                    "qty": t.order.totalQuantity,
                    "type": t.order.orderType.lower(),
                    "limit_price": t.order.lmtPrice if t.order.orderType == "LMT" else None,
                    "status": t.orderStatus.status,
                    "submitted": None,
                }
                for t in self.ib.trades()
            ]

        return self._run(go())

    def submit_order(self, req: OrderRequest) -> str:
        if req.is_option or req.take_profit or req.stop_loss:
            raise ValueError("Options and bracket orders are only supported through Alpaca in this app.")

        async def go():
            await self._ensure()
            contract = Stock(req.symbol, "SMART", "USD")
            if not await self.ib.qualifyContractsAsync(contract):
                raise ValueError(f"IBKR does not recognise {req.symbol}")
            action = "BUY" if req.side == "buy" else "SELL"
            tif = "GTC" if req.tif == "gtc" else "DAY"
            if req.order_type == "limit":
                order = LimitOrder(action, req.qty, req.limit_price, tif=tif)
            elif req.order_type == "stop":
                order = StopOrder(action, req.qty, req.stop_price, tif=tif)
            else:
                order = MarketOrder(action, req.qty, tif=tif)
            return str(self.ib.placeOrder(contract, order).order.orderId)

        return self._run(go())

    def cancel_order(self, order_id: str) -> None:
        async def go():
            await self._ensure()
            for t in self.ib.trades():
                if str(t.order.orderId) == order_id:
                    self.ib.cancelOrder(t.order)
                    return
            raise ValueError(f"No open IBKR order {order_id}")

        self._run(go())
