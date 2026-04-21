import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from bitvavo.BitvavoClient import BitvavoClient

from .const import CONF_BALANCES, CONF_TICKERS, CONF_ORDERS

_LOGGER = logging.getLogger(__name__)


class BitvavoCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api_key, api_secret):
        super().__init__(
            hass,
            _LOGGER,
            name="bitvavo_enhanced",
            update_interval=timedelta(seconds=60),
        )

        self.client = BitvavoClient(api_key, api_secret)

    async def _async_update_data(self):
        balances_raw = await self.client.get_balance()
        tickers_raw = await self.client.get_price_ticker()
        orders_raw = await self.client.get_open_orders()

        portfolio = {}

        # ---------------------------------
        # 1. BALANCES + STAKING
        # ---------------------------------
        for b in balances_raw:
            symbol = b.get("symbol")

            available = float(b.get("available", 0) or 0)
            in_order = float(b.get("inOrder", 0) or 0)
            staked = float(b.get("staked", 0) or 0)
            lent = float(b.get("lent", 0) or 0)

            portfolio[symbol] = {
                "available": available,
                "inOrder": in_order,
                "staked": staked,
                "lent": lent,
                "orders": [],
                "total": available + in_order + staked + lent,
            }

        # ---------------------------------
        # 2. OPEN ORDERS (correct mapped)
        # ---------------------------------
        for o in orders_raw:
            market = o.get("market", "")
            if "-" not in market:
                continue

            base, quote = market.split("-")

            portfolio.setdefault(base, {
                "available": 0,
                "inOrder": 0,
                "staked": 0,
                "lent": 0,
                "orders": [],
                "total": 0,
            })

            portfolio[base]["orders"].append({
                "market": market,
                "side": o.get("side"),
                "amount": o.get("amount"),
                "price": o.get("price"),
                "status": o.get("status"),
            })

        # ---------------------------------
        # 3. CLEAN OUTPUT
        # ---------------------------------
        display_portfolio = {
            k: v for k, v in portfolio.items()
            if v["total"] > 0 or len(v["orders"]) > 0
        }

        return {
            CONF_BALANCES: display_portfolio,
            CONF_TICKERS: {t["market"]: t for t in tickers_raw},
            CONF_ORDERS: orders_raw,
            "raw_portfolio": portfolio,
        }