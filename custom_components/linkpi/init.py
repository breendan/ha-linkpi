import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL
from .encoderapi import LinkPiEncoder
from .coordinator import LinkPiCoordinator

PLATFORMS = ["sensor"]
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LinkPi integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data[CONF_HOST]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    encoder = LinkPiEncoder(host, username, password)

    try:
        await encoder.login()
        _LOGGER.info("LinkPi Encoder login executed successfully at setup.")
    except Exception as e:
        _LOGGER.error(f"Failed to login to LinkPi Encoder during setup: {e}")
        return False

    coordinator = LinkPiCoordinator(hass, encoder, host, timedelta(seconds=scan_interval))
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "encoder": encoder,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update for scan interval."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: LinkPiCoordinator = data["coordinator"]

    new_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator.update_interval = timedelta(seconds=new_interval)

    _LOGGER.info("Updated scan interval to %s seconds", new_interval)

    # Optional: force an immediate refresh
    await coordinator.async_request_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if data and "encoder" in data:
            await data["encoder"].close()
    return unload_ok
