import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_BALANCES, ATTRIBUTION

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        BitvavoAssetSensor(coordinator, asset)
        for asset in coordinator.data.get(CONF_BALANCES, {})
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
        data = self.coordinator.data[CONF_BALANCES].get(self._asset, {})
        return round(data.get("total", 0), 8)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data[CONF_BALANCES].get(self._asset, {})

        return {
            "available": data.get("available", 0),
            "in_order": data.get("inOrder", 0),
            "staked": data.get("staked", 0),
            "lent": data.get("lent", 0),
            "orders": data.get("orders", []),
            "orders_count": len(data.get("orders", [])),
            "total": data.get("total", 0),
            "eur_price": data.get("eur_price"),
            "eur_value": data.get("eur_value"),
            "attribution": ATTRIBUTION,
        }
