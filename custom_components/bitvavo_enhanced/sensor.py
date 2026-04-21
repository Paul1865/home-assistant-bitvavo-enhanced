import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_BALANCES, ATTRIBUTION

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        BitvavoAssetSensor(coordinator, asset)
        for asset in coordinator.data[CONF_BALANCES]
    ]

    async_add_entities(entities)


class BitvavoAssetSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, asset):
        super().__init__(coordinator)

        self._asset = asset
        self._attr_name = f"Bitvavo {asset}"
        self._attr_unique_id = f"bitvavo_{asset}"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self):
        data = self.coordinator.data[CONF_BALANCES][self._asset]
        return round(data["total"], 8)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data[CONF_BALANCES][self._asset]

        return {
            "available": data["available"],
            "in_order": data["inOrder"],
            "staked": data["staked"],
            "lent": data["lent"],
            "orders": data["orders"],
            "total": data["total"],
            "attribution": ATTRIBUTION,
        }