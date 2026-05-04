import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import CURRENCY_EURO
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, CONF_BALANCES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    balances = coordinator.data.get(CONF_BALANCES) or {}

    # Per-asset sensors
    for asset in balances:
        entities.append(BitvavoAssetSensor(coordinator, asset))
        entities.append(BitvavoEurValueSensor(coordinator, asset))

    # Total portfolio sensor
    entities.append(BitvavoPortfolioTotalSensor(coordinator))

    async_add_entities(entities)


def _device_info() -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, "bitvavo_enhanced")},
        name="Bitvavo Enhanced",
        manufacturer="Bitvavo",
        model="Portfolio Tracker",
        entry_type="service",
    )


class BitvavoAssetSensor(CoordinatorEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, asset: str):
        super().__init__(coordinator)
        self._asset = asset
        self._attr_has_entity_name = True
        self._attr_name = f"{asset} Balance"
        self._attr_unique_id = f"{DOMAIN}_{asset}_balance"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info()

    @property
    def native_value(self):
        data = self.coordinator.data.get(CONF_BALANCES, {}).get(self._asset, {})
        return data.get("total", 0)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data.get(CONF_BALANCES, {}).get(self._asset, {})

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

            # Cost basis & PnL
            "cost_basis": data.get("cost_basis"),
            "avg_buy_price": data.get("avg_buy_price"),
            "pnl": data.get("pnl"),
            "pnl_pct": data.get("pnl_pct"),
        }


class BitvavoEurValueSensor(CoordinatorEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_device_class = "monetary"

    def __init__(self, coordinator, asset: str):
        super().__init__(coordinator)
        self._asset = asset
        self._attr_has_entity_name = True
        self._attr_name = f"{asset} EUR Value"
        self._attr_unique_id = f"{DOMAIN}_{asset}_eur"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info()

    @property
    def native_value(self):
        data = self.coordinator.data.get(CONF_BALANCES, {}).get(self._asset, {})
        return data.get("eur_value")


class BitvavoPortfolioTotalSensor(CoordinatorEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_device_class = "monetary"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_has_entity_name = True
        self._attr_name = "Total EUR"
        self._attr_unique_id = f"{DOMAIN}_total_eur"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info()

    @property
    def native_value(self):
        return self.coordinator.data.get("total_eur")
