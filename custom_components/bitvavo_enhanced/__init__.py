from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import BitvavoAPI
from .coordinator import BitvavoCoordinator
from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    api = BitvavoAPI(
        entry.data["api_key"],
        entry.data["api_secret"],
    )

    coordinator = BitvavoCoordinator(hass, api)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator
    }

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    await coordinator.async_shutdown()
    return True