from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_BALANCES, CONF_TICKERS, ATTRIBUTION
from .device import get_device


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    known_assets = set()

    entities = [
        PortfolioSensor(coordinator),
        TotalValueSensor(coordinator),
    ]

    async_add_entities(entities)

    async def async_update_entities():
        new_entities = []

        balances = coordinator.data.get(CONF_BALANCES, {})

        for asset in balances:
            if asset not in known_assets:
                known_assets.add(asset)
                new_entities.append(BalanceSensor(coordinator, asset))

        if new_entities:
            async_add_entities(new_entities)

    await async_update_entities()
    coordinator.async_add_listener(async_update_entities)


class BalanceSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, asset):
        super().__init__(coordinator)
        self._asset = asset

        self._attr_name = f"Bitvavo {asset} Balance"
        self._attr_unique_id = f"bitvavo_balance_{asset}"
        self._attr_device_info = get_device()

        self._attr_state_class = "measurement"

    def _get(self, key):
        return float(
            self.coordinator.data[CONF_BALANCES]
            .get(self._asset, {})
            .get(key, 0)
        )

    @property
    def state(self):
        return round(self._get("total"), 6)

    @property
    def extra_state_attributes(self):
        return {
            "available": self._get("available"),
            "in_order": self._get("inOrder"),
            "staked": self._get("staked"),
            "lent": self._get("lent"),
            ATTRIBUTION: ATTRIBUTION,
        }


class PortfolioSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)

        self._attr_name = "Bitvavo Portfolio"
        self._attr_unique_id = "bitvavo_portfolio"
        self._attr_device_info = get_device()

    @property
    def state(self):
        return len(self.coordinator.data[CONF_BALANCES])

    @property
    def extra_state_attributes(self):
        return self.coordinator.data[CONF_BALANCES]


class TotalValueSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)

        self._attr_name = "Bitvavo Total Value EUR"
        self._attr_unique_id = "bitvavo_total_value_eur"
        self._attr_unit_of_measurement = "EUR"
        self._attr_device_info = get_device()

        self._attr_state_class = "measurement"
        self._attr_device_class = "monetary"

    @property
    def state(self):
        total = 0

        balances = self.coordinator.data[CONF_BALANCES]
        tickers = self.coordinator.data[CONF_TICKERS]

        for asset, data in balances.items():
            amount = data["total"]

            if asset == "EUR":
                total += amount
                continue

            pair = f"{asset}-EUR"
            if pair in tickers:
                price = float(tickers[pair]["price"])
                total += amount * price

        return round(total, 2)