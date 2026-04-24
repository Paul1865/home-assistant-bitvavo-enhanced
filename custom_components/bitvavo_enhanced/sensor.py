
import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_BALANCES, ATTRIBUTION

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []

    for asset in coordinator.data.get(CONF_BALANCES, {}):
        entities.append(BitvavoAssetSensor(coordinator, asset))
        entities.append(BitvavoEurValueSensor(coordinator, asset))

    # Portfolio total sensor
    entities.append(BitvavoPortfolioTotalSensor(coordinator))

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


class BitvavoEurValueSensor(CoordinatorEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "€"
    _attr_device_class = "monetary"

    def __init__(self, coordinator, asset: str):
        super().__init__(coordinator)
        self._asset = asset
        self._attr_name = f"Bitvavo {asset} EUR Value"
        self._attr_unique_id = f"bitvavo_enhanced_{asset}_eur_value"

    @property
    def state(self):
        data = self.coordinator.data[CONF_BALANCES].get(self._asset, {})
        value = data.get("eur_value")
        return round(value, 2) if value is not None else 0


class BitvavoPortfolioTotalSensor(CoordinatorEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Bitvavo Total EUR"
    _attr_unique_id = "bitvavo_enhanced_total_eur"
    _attr_native_unit_of_measurement = "€"
    _attr_device_class = "monetary"

    def __init__(self, coordinator):
        super().__init__(coordinator)

    @property
    def state(self):
        balances = self.coordinator.data.get(CONF_BALANCES, {})
        total = sum(
            asset.get("eur_value", 0) or 0
            for asset in balances.values()
        )
        return round(total, 2)
