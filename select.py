"""Select platform for Jiachao IoT."""
import logging

from homeassistant.components.select import SelectEntity
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
    """Set up selects from config entry."""
    hub: JiachaoHub = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device in hub.devices.values():
        for spec in device.get_entity_specs():
            if spec["platform"] == "select":
                entities.append(JiachaoSelect(device, spec))
    async_add_entities(entities)


class JiachaoSelect(SelectEntity):
    """Generic select entity driven by device spec."""

    _attr_has_entity_name = True

    def __init__(self, device, spec: dict) -> None:
        """Initialize select entity."""
        self._device = device
        self._spec = spec

        self._attr_translation_key = spec["translation_key"]
        self._attr_unique_id = f"{device.device_id}_{spec['unique_id_suffix']}"
        self._attr_device_info = get_device_info(device)

        extra = spec.get("extra", {})
        self._attr_options = extra.get("options", [])
        self._value_getter = extra.get("value_getter")
        self._state_key = spec.get("state_key")

        device.register_callback(self._update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Clean up callback."""
        self._device.remove_callback(self._update_callback)

    @callback
    def _update_callback(self) -> None:
        """Schedule state update."""
        self.async_write_ha_state()

    def _get_current_value(self):
        """Get current value from device state."""
        if self._value_getter is not None:
            return self._value_getter()
        if self._state_key is not None:
            return self._device.state.get(self._state_key)
        return None

    @property
    def current_option(self) -> str | None:
        """Return current selected option."""
        value = self._get_current_value()
        if value is None:
            return None
        if isinstance(value, int) and 0 <= value < len(self._attr_options):
            return self._attr_options[value]
        if isinstance(value, str) and value in self._attr_options:
            return value
        return None

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        methods = self._spec.get("methods", {})
        if "select_option" not in methods:
            return
        if option in self._attr_options:
            extra = self._spec.get("extra", {})
            send_index = extra.get("send_index", True)
            if send_index:
                value = self._attr_options.index(option)
            else:
                value = option
            await methods["select_option"](value)