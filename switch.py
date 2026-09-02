"""Switch platform for Jiachao IoT."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .device_base import get_device_info
from .hub import JiachaoHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches from config entry."""
    hub: JiachaoHub = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device in hub.devices.values():
        for spec in device.get_entity_specs():
            if spec["platform"] == "switch":
                entities.append(JiachaoSwitch(device, spec))
    async_add_entities(entities)


class JiachaoSwitch(SwitchEntity):
    """Generic switch entity driven by device spec."""

    _attr_has_entity_name = True

    def __init__(self, device, spec: dict) -> None:
        """Initialize switch entity."""
        self._device = device
        self._spec = spec

        self._attr_translation_key = spec["translation_key"]
        self._attr_unique_id = f"{device.device_id}_{spec['unique_id_suffix']}"
        self._attr_device_info = get_device_info(device)

        extra = spec.get("extra", {})
        self._value_getter = extra.get("value_getter")
        self._state_key = spec.get("state_key")
        self._attr_icon = extra.get("icon")

        device.register_callback(self._update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Clean up callback."""
        self._device.remove_callback(self._update_callback)

    @callback
    def _update_callback(self) -> None:
        """Schedule state update."""
        self.async_write_ha_state()

    def _get_current_value(self) -> bool | None:
        """Get current switch state."""
        if self._value_getter is not None:
            val = self._value_getter()
            return bool(val) if val is not None else None
        if self._state_key is not None:
            val = self._device.state.get(self._state_key)
            return bool(val) if val is not None else None
        return None

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        return self._get_current_value()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        methods = self._spec.get("methods", {})
        on_method = methods.get("turn_on")
        if on_method is not None:
            await on_method()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        methods = self._spec.get("methods", {})
        off_method = methods.get("turn_off")
        if off_method is not None:
            await off_method()