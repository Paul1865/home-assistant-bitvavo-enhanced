import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    CONF_BALANCES,
    CONF_TICKERS,
    CONF_ORDERS,
)

_LOGGER = logging.getLogger(__name__)


class BitvavoCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, poll_interval=60, debug=False):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=poll_interval),
        )

        self.api = api
        self.debug = debug

    def _get_eur_price(self, symbol, tickers):
        if symbol == "EUR":
            return 1.0

        direct = f"{symbol}-EUR"
        if direct in tickers:
            return float(tickers[direct]["price"])

        usdt_pair = f"{symbol}-USDT"
        if usdt_pair in tickers and "USDT-EUR" in tickers:
            return float(tickers[usdt_pair]["price"]) * float(tickers["USDT-EUR"]["price"])

        btc_pair = f"{symbol}-BTC"
        if btc_pair in tickers and "BTC-EUR" in tickers:
            return float(tickers[btc_pair]["price"]) * float(tickers["BTC-EUR"]["price"])

        return None

    async def _async_update_data(self):
        balances_raw, staking_raw, tickers_raw, orders_raw = await self._fetch_all()

        if self.debug:
            _LOGGER.warning("Bitvavo Enhanced Debug: balances=%s", balances_raw)
            _LOGGER.warning("Bitvavo Enhanced Debug: staking=%s", staking_raw)
            _LOGGER.warning("Bitvavo Enhanced Debug: tickers=%s", tickers_raw)
            _LOGGER.warning("Bitvavo Enhanced Debug: orders=%s", orders_raw)

        tickers_map = {t["market"]: t for t in tickers_raw}

        portfolio: dict[str, dict] = {}

        # 1. Balances + flexible staking
        for b in balances_raw:
            symbol = b.get("symbol")

            available = float(b.get("available", 0) or 0)
            in_order = float(b.get("inOrder", 0) or 0)
            staked_flexible = float(b.get("staked", 0) or 0)
            lent = float(b.get("lent", 0) or 0)

            portfolio[symbol] = {
                "available": available,
                "inOrder": in_order,
                "staked_flexible": staked_flexible,
                "staked_fixed": 0.0,
                "lent": lent,
                "orders": [],
            }

        # 2. Fixed staking
        for s in staking_raw:
            symbol = s.get("symbol")
            amount = float(s.get("amount", 0) or 0)

            if symbol not in portfolio:
                portfolio[symbol] = {
                    "available": 0,
                    "inOrder": 0,
                    "staked_flexible": 0.0,
                    "staked_fixed": 0.0,
                    "lent": 0.0,
                    "orders": [],
                }

            portfolio[symbol]["staked_fixed"] += amount

        # 3. Total + EUR value
        for symbol, data in portfolio.items():
            total = (
                data["available"]
                + data["inOrder"]
                + data["staked_flexible"]
                + data["staked_fixed"]
                + data["lent"]
            )
            data["total"] = total

            eur_price = self._get_eur_price(symbol, tickers_map)
            if eur_price is not None:
                data["eur_price"] = eur_price
                data["eur_value"] = eur_price * total
            else:
                data["eur_price"] = None
                data["eur_value"] = None

        # 4. Open orders
        for o in orders_raw:
            market = o.get("market", "")
            if "-" not in market:
                continue

            base, _ = market.split("-")

            if base not in portfolio:
                portfolio[base] = {
                    "available": 0,
                    "inOrder": 0,
                    "staked_flexible": 0.0,
                    "staked_fixed": 0.0,
                    "lent": 0.0,
                    "orders": [],
                    "total": 0.0,
                    "eur_price": None,
                    "eur_value": None,
                }

            portfolio[base]["orders"].append(o)

        return {
            CONF_BALANCES: portfolio,
            CONF_TICKERS: tickers_map,
            CONF_ORDERS: orders_raw,
            "raw_portfolio": portfolio,
        }

    async def _fetch_all(self):
        balances = await self.api.get_balance()
        staking = await self.api.get_staking_balance()
        tickers = await self.api.get_tickers()
        orders = await self.api.get_open_orders()
        return balances, staking, tickers, orders
