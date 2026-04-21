import asyncio
import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from bitvavo.BitvavoClient import BitvavoClient

from .const import CONF_BALANCES, CONF_TICKERS
from .websocket import BitvavoWebsocket

_LOGGER = logging.getLogger(__name__)


class BitvavoCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api_key, api_secret):
        super().__init__(
            hass,
            _LOGGER,
            name="bitvavo",
            update_interval=timedelta(seconds=60),
        )

        self.client = BitvavoClient(api_key, api_secret)
        self.ws = BitvavoWebsocket(self)

    async def _async_update_data(self):
        balances_raw = await self.client.get_balance()
        tickers_raw = await self.client.get_price_ticker()

        balances_map = {b["symbol"]: b for b in balances_raw}

        # -------------------------------------------------
        # FULL BALANCE STRUCTURE (incl staking/lending)
        # -------------------------------------------------
        full_balances = {}

        for b in balances_raw:
            symbol = b["symbol"]

            available = float(b.get("available", 0))
            in_order = float(b.get("inOrder", 0))
            staked = float(b.get("staked", 0))
            lent = float(b.get("lent", 0))

            total = available + in_order + staked + lent

            full_balances[symbol] = {
                "available": available,
                "inOrder": in_order,
                "staked": staked,
                "lent": lent,
                "total": total,
            }

        # -------------------------------------------------
        # FILTERED VIEW (NO ZERO ASSETS IN UI)
        # -------------------------------------------------
        display_balances = {
            symbol: data
            for symbol, data in full_balances.items()
            if data["total"] > 0
        }

        # -------------------------------------------------
        # RETURN DATASET
        # -------------------------------------------------
        return {
            CONF_BALANCES: display_balances,
            CONF_TICKERS: {t["market"]: t for t in tickers_raw},

            # RAW DATA (handig voor debug / future features)
            "raw_balances": full_balances,
        }

    async def async_config_entry_first_refresh(self):
        await super().async_config_entry_first_refresh()

        # start websocket (realtime prices)
        asyncio.create_task(self.ws.connect())