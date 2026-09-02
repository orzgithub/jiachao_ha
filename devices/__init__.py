"""Device factory for Jiachao IoT."""

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from ..device_base import JiachaoDeviceBase
from .sap import JiachaoSAPDevice

_LOGGER = logging.getLogger(__name__)

# Registry of supported device types
DEVICE_TYPES: dict[str, type[JiachaoDeviceBase]] = {
    "SAP": JiachaoSAPDevice,
    # Add more types here as they are implemented
}

def create_device(
    hass: HomeAssistant,
    hub,
    device_info: dict[str, Any],
) -> JiachaoDeviceBase | None:
    """Create a device instance based on dtype."""
    dtype = device_info.get("dtype")
    if dtype not in DEVICE_TYPES:
        _LOGGER.warning("Unsupported device type: %s", dtype)
        return None
    device_class = DEVICE_TYPES[dtype]
    return device_class(hass, hub, device_info)