import logging
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "bitvavo_enhanced_cost_basis"


class CostBasisStorage:
    def __init__(self, hass):
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict = {}

    async def async_load(self):
        stored = await self._store.async_load()
        if stored:
            self.data = stored
        else:
            self.data = {}

    async def async_save(self):
        await self._store.async_save(self.data)

    def update(self, symbol: str, amount: float, cost: float):
        self.data[symbol] = {
            "amount": amount,
            "cost": cost,
        }
