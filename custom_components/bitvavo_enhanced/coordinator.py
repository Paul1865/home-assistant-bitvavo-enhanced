import asyncio
import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, CONF_BALANCES
from .storage import CostBasisStorage

_LOGGER = logging.getLogger(__name__)


class BitvavoCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, poll_interval: int = 60) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=poll_interval),
        )

        self.api = api
        self._data: dict = {}
        self._ws_prices: dict[str, float] = {}
        self._ws_task: asyncio.Task | None = None

        self._pnl_threshold = 0
        self._last_alert_state: dict = {}

        # 🔥 STORAGE
        self._storage = CostBasisStorage()
        self._storage.load()

    async def async_config_entry_first_refresh(self) -> None:
        await self._async_poll_update()
        self._ws_task = self.hass.loop.create_task(self._run_websocket())

    async def async_shutdown(self) -> None:
        if self._ws_task:
            self._ws_task.cancel()
            self._ws_task = None
        await self.api.close()

    async def _async_update_data(self):
        await self._async_poll_update()
        return self._data

    async def _fetch_all_trades(self):
        trades = await self.api.get_trades()
        if not trades or isinstance(trades, dict):
            return []
        return trades

    async def _fetch_all(self):
        balances = await self.api.get_balance() or []
        staking = await self.api.get_staking_balance() or []
        tickers = await self.api.get_tickers() or []
        orders = await self.api.get_open_orders() or []
        trades = await self._fetch_all_trades() or []

        return balances, staking, tickers, orders, trades

    async def _async_poll_update(self):
        balances, staking, tickers, orders, trades = await self._fetch_all()

        tickers_map = {
            t.get("market"): t for t in tickers if t.get("market")
        }

        cost_basis = self._calculate_cost_basis(trades)

        portfolio = self._build_portfolio(
            balances, staking, tickers_map, orders, cost_basis
        )

        self._process_update(portfolio)

    async def _run_websocket(self):
        while True:
            try:
                async with self.api.session.ws_connect(
                    "wss://ws.bitvavo.com/v2/", heartbeat=20
                ) as ws:

                    markets = [
                        f"{symbol}-EUR"
                        for symbol in self._data.get(CONF_BALANCES, {})
                        if symbol != "EUR"
                    ]

                    if markets:
                        await ws.send_json(
                            {
                                "action": "subscribe",
                                "channels": [
                                    {"name": "ticker", "markets": markets}
                                ],
                            }
                        )

                    async for msg in ws:
                        try:
                            data = await msg.json()
                        except Exception:
                            continue

                        market = data.get("market")
                        price = data.get("price")

                        if market and price is not None:
                            try:
                                self._ws_prices[market] = float(price)
                            except Exception:
                                continue
                            self._recalculate_prices()

            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.warning("WS reconnect in 5s: %s", e)
                await asyncio.sleep(5)

    def _process_update(self, portfolio: dict):
        total_eur = sum(v.get("eur_value") or 0.0 for v in portfolio.values())
        total_pnl = sum(v.get("pnl") or 0.0 for v in portfolio.values())

        new_data = {
            CONF_BALANCES: portfolio,
            "total_eur": total_eur,
            "total_pnl": total_pnl,
            "total_pnl_pct": (total_pnl / total_eur * 100) if total_eur else 0.0,
        }

        if new_data != self._data:
            self._data = new_data
            self.async_set_updated_data(self._data)

    def _recalculate_prices(self):
        portfolio = self._data.get(CONF_BALANCES, {})
        updated = False

        for symbol, data in portfolio.items():
            market = f"{symbol}-EUR"

            if market in self._ws_prices:
                price = self._ws_prices[market]
                total = data.get("total", 0.0)
                new_value = price * total

                if data.get("eur_value") != new_value:
                    data["eur_price"] = price
                    data["eur_value"] = new_value

                    cost_basis = data.get("cost_basis") or 0.0
                    pnl = new_value - cost_basis

                    data["pnl"] = pnl
                    data["pnl_pct"] = (
                        (pnl / cost_basis) * 100 if cost_basis else 0.0
                    )

                    updated = True

        if updated:
            self._process_update(portfolio)

    def _build_portfolio(
        self,
        balances,
        staking,
        tickers_map,
        orders,
        cost_basis,
    ):
        portfolio: dict[str, dict] = {}

        for b in balances:
            symbol = b.get("symbol")
            if not symbol:
                continue

            portfolio[symbol] = {
                "available": float(b.get("available", 0.0)),
                "inOrder": float(b.get("inOrder", 0.0)),
                "staked_flexible": float(b.get("staked", 0.0)),
                "staked_fixed": 0.0,
                "lent": float(b.get("lent", 0.0)),
                "orders": [],
            }

        for s in staking:
            symbol = s.get("symbol")
            if not symbol:
                continue

            portfolio.setdefault(symbol, {
                "available": 0.0,
                "inOrder": 0.0,
                "staked_flexible": 0.0,
                "staked_fixed": 0.0,
                "lent": 0.0,
                "orders": [],
            })

            portfolio[symbol]["staked_fixed"] += float(s.get("amount", 0.0))

        for symbol, data in portfolio.items():
            total = sum([
                data["available"],
                data["inOrder"],
                data["staked_flexible"],
                data["staked_fixed"],
                data["lent"],
            ])
            data["total"] = total

            price = self._get_price(symbol, tickers_map)
            eur_value = price * total if price is not None else 0.0

            data["eur_price"] = price
            data["eur_value"] = eur_value

            cb = cost_basis.get(symbol)

            if cb and cb.get("amount", 0.0) > 0.0:
                avg_price = cb["cost"] / cb["amount"]
                cost_total = avg_price * total
            else:
                # 🔥 fallback
                cost_total = eur_value
                avg_price = eur_value / total if total else 0.0

            pnl = eur_value - cost_total

            data["cost_basis"] = cost_total
            data["avg_buy_price"] = avg_price
            data["pnl"] = pnl
            data["pnl_pct"] = (
                (pnl / cost_total) * 100 if cost_total else 0.0
            )

        return portfolio

    def _get_price(self, symbol: str, tickers_map: dict):
        if symbol == "EUR":
            return 1.0

        market = f"{symbol}-EUR"

        if market in self._ws_prices:
            return self._ws_prices[market]

        ticker = tickers_map.get(market)
        if ticker:
            try:
                return float(ticker.get("price", 0.0))
            except Exception:
                return None

        if symbol in ("USDT", "USDC"):
            return 1.0

        return None

    def _calculate_cost_basis(self, trades):
        result = {}

        # start met opgeslagen data
        for symbol, stored in self._storage.data.items():
            result[symbol] = {
                "amount": stored.get("amount", 0.0),
                "cost": stored.get("cost", 0.0),
            }

        for t in trades:
            market = t.get("market")
            if not market:
                continue

            symbol = market.split("-")[0]

            try:
                amount = float(t.get("amount", 0.0))
                price = float(t.get("price", 0.0))
            except Exception:
                continue

            side = t.get("side")
            if not side:
                continue

            result.setdefault(symbol, {"amount": 0.0, "cost": 0.0})
            pos = result[symbol]

            if side == "buy":
                pos["cost"] += amount * price
                pos["amount"] += amount

            elif side == "sell" and pos["amount"] > 0:
                avg_price = pos["cost"] / pos["amount"]
                pos["amount"] -= amount
                pos["cost"] -= avg_price * amount

        # opslaan
        for symbol, data in result.items():
            self._storage.update(symbol, data["amount"], data["cost"])

        self._storage.save()

        return result