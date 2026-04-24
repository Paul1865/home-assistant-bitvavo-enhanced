import logging
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_POLL_INTERVAL,
)
from .api import BitvavoAPI
from .coordinator import BitvavoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})

    session = aiohttp.ClientSession()
    api = BitvavoAPI(
        entry.data[CONF_API_KEY],
        entry.data[CONF_API_SECRET],
        session,
    )

    poll_interval = entry.options.get(CONF_POLL_INTERVAL, 60)

    coordinator = BitvavoCoordinator(
        hass,
        api,
        poll_interval=poll_interval,
        debug=entry.options.get("debug", False),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "session": session,
    }

    
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    # Reload integratie bij opties-wijziging
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    data = hass.data[DOMAIN].pop(entry.entry_id, None)

    if data and "session" in data:
        await data["session"].close()

    
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])
