from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_API_KEY, CONF_API_SECRET
from .coordinator import BitvavoCoordinator

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    api_key = entry.data[CONF_API_KEY]
    api_secret = entry.data[CONF_API_SECRET]

    coordinator = BitvavoCoordinator(hass, api_key, api_secret)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True