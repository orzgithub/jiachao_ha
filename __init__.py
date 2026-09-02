"""Jiachao IoT integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN, CONF_TOKEN, CONF_USER_ID, CONF_ZONE, CONF_DEVICES
from .hub import JiachaoHub

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.FAN,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.SENSOR,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Jiachao IoT from a config entry."""
    data = entry.data
    hub = JiachaoHub(
        hass=hass,
        token=data[CONF_TOKEN],
        user_id=data[CONF_USER_ID],
        zone=data[CONF_ZONE],
        devices_info=data[CONF_DEVICES],
    )
    await hub.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hub: JiachaoHub = hass.data[DOMAIN].pop(entry.entry_id)
    await hub.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)