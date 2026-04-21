import asyncio
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
            symbol = b["symbol"]

            available = float(b.get("available", 0))
            in_order = float(b.get("inOrder", 0))
            staked = float(b.get("staked", 0))
            lent = float(b.get("lent", 0))

            portfolio[symbol] = {
                "available": available,
                "inOrder": in_order,
                "staked": staked,
                "lent": lent,
                "orders": 0,
                "total": available + in_order + staked + lent,
            }

        # ---------------------------------
        # 2. OPEN ORDERS (BTC FIX)
        # ---------------------------------
        for o in orders_raw:
            market = o.get("market", "")
            symbol = market.split("-")[0] if "-" in market else market

            if symbol not in portfolio:
                portfolio[symbol] = {
                    "available": 0,
                    "inOrder": 0,
                    "staked": 0,
                    "lent": 0,
                    "orders": 0,
                    "total": 0,
                }

            portfolio[symbol]["orders"] += 1

        # ---------------------------------
        # 3. FILTER CLEAN VIEW
        # ---------------------------------
        display_portfolio = {
            k: v for k, v in portfolio.items()
            if v["total"] > 0 or v["orders"] > 0
        }

        return {
            CONF_BALANCES: display_portfolio,
            CONF_TICKERS: {t["market"]: t for t in tickers_raw},
            CONF_ORDERS: orders_raw,
            "raw_portfolio": portfolio,
        }

    async def async_config_entry_first_refresh(self):
        await super().async_config_entry_first_refresh()