from .const import DOMAIN
from .coordinator import BitvavoCoordinator


async def async_setup_entry(hass, entry):
    coordinator = BitvavoCoordinator(
        hass,
        entry.data["api_key"],
        entry.data["api_secret"],
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)