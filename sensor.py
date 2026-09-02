"""Sensor platform for Jiachao IoT."""
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .hub import JiachaoHub
from .device_base import get_device_info

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from config entry."""
    hub: JiachaoHub = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device in hub.devices.values():
        for spec in device.get_entity_specs():
            if spec["platform"] == "sensor":
                entities.append(JiachaoSensor(device, spec))
    async_add_entities(entities)


class JiachaoSensor(SensorEntity):
    """Generic sensor entity driven by device spec."""

    _attr_has_entity_name = True

    def __init__(self, device, spec: dict) -> None:
        """Initialize sensor entity."""
        self._device = device
        self._spec = spec

        self._attr_translation_key = spec["translation_key"]
        self._attr_unique_id = f"{device.device_id}_{spec['unique_id_suffix']}"
        self._attr_device_info = get_device_info(device)

        extra = spec.get("extra", {})
        self._value_getter = extra.get("value_getter")
        self._state_key = spec.get("state_key")

        # Device class
        device_class = extra.get("device_class")
        if device_class:
            try:
                self._attr_device_class = SensorDeviceClass(device_class)
            except ValueError:
                self._attr_device_class = None
        else:
            self._attr_device_class = None

        # State class
        state_class = extra.get("state_class")
        if state_class:
            try:
                self._attr_state_class = SensorStateClass(state_class)
            except ValueError:
                self._attr_state_class = None
        else:
            self._attr_state_class = None

        self._attr_native_unit_of_measurement = extra.get("unit")
        self._attr_icon = extra.get("icon")

        if "precision" in extra:
            self._attr_suggested_display_precision = extra["precision"]

        device.register_callback(self._update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Clean up callback."""
        self._device.remove_callback(self._update_callback)

    def _update_callback(self) -> None:
        """Schedule state update."""
        self.async_write_ha_state()

    @property
    def native_value(self):
        """Return sensor value."""
        if self._value_getter is not None:
            return self._value_getter()
        if self._state_key is not None:
            return self._device.state.get(self._state_key)
        return None