"""Hub for Jiachao IoT devices."""

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .const import CONF_TOKEN, CONF_USER_ID, CONF_ZONE, CONF_DEVICES
from .device_base import JiachaoDeviceBase
from .devices import create_device

_LOGGER = logging.getLogger(__name__)

class JiachaoHub:
    """Central hub managing all Jiachao devices."""

    def __init__(
        self,
        hass: HomeAssistant,
        token: str,
        user_id: str,
        zone: str,
        devices_info: list[dict[str, Any]],
    ) -> None:
        """Initialize hub."""
        self.hass = hass
        self.token = token
        self.user_id = user_id
        self.zone = zone
        self.devices: dict[str, JiachaoDeviceBase] = {}

        for device_info in devices_info:
            device = create_device(hass, self, device_info)
            if device is not None:
                self.devices[device.device_id] = device

    async def async_start(self) -> None:
        """Start all devices."""
        for device in self.devices.values():
            await device.async_start()

    async def async_stop(self) -> None:
        """Stop all devices."""
        for device in self.devices.values():
            await device.async_stop()

    def get_username(self, device_id: str) -> str:
        """Construct MQTT username."""
        return f"{device_id}_{self.zone}{self.user_id}"