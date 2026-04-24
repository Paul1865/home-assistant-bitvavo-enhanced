import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_BALANCES, ATTRIBUTION

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [
        BitvavoAssetSensor(coordinator, asset)
        for asset in coordinator.data.get(CONF_BALANCES, {})
    ]

    async_add_entities(entities)


class BitvavoAssetSensor(CoordinatorEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, asset: str):
        super().__init__(coordinator)
        self._asset = asset
        self._attr_name = f"Bitvavo {asset}"
        self._attr_unique_id = f"bitvavo_enhanced_{asset}"

    @property
    def state(self):
        data = self.coordinator.data[CONF_BALANCES].get(self._asset, {})
        return round(data.get("total", 0), 8)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data[CONF_BALANCES].get(self._asset, {})

        staked_flexible = data.get("staked_flexible", 0.0)
        staked_fixed = data.get("staked_fixed", 0.0)

        return {
            "available": data.get("available", 0.0),
            "in_order": data.get("inOrder", 0.0),
            "staked_flexible": staked_flexible,
            "staked_fixed": staked_fixed,
            "staked_total": staked_flexible + staked_fixed,
            "lent": data.get("lent", 0.0),
            "orders": data.get("orders", []),
            "orders_count": len(data.get("orders", [])),
            "total": data.get("total", 0.0),
            "eur_price": data.get("eur_price"),
            "eur_value": data.get("eur_value"),
            "attribution": ATTRIBUTION,
        }
