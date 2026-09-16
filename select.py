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
        self._attr_options = list(extra.get("options", []))
        self._option_params = extra.get("option_params")
        self._option_values = extra.get("option_values")
        self._value_getter = extra.get("value_getter")
        self._state_key = spec.get("state_key")
        self._mode_key_getter = extra.get("mode_key_getter")

        device.register_callback(self._update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Clean up callback."""
        self._device.remove_callback(self._update_callback)

    @callback
    def _update_callback(self) -> None:
        """Schedule state update."""
        self.async_write_ha_state()

    @property
    def current_option(self) -> str | None:
        """Return current selected option key."""
        if self._mode_key_getter is not None:
            return self._mode_key_getter()
        value = None
        if self._value_getter is not None:
            value = self._value_getter()
        elif self._state_key is not None:
            value = self._device.state.get(self._state_key)

        if value is None:
            return None
        if self._option_values is None:
            return None
        try:
            idx = self._option_values.index(value)
            return self._attr_options[idx]
        except ValueError:
            return None

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        methods = self._spec.get("methods", {})
        if "select_option" not in methods:
            return

        if option not in self._attr_options:
            _LOGGER.warning(
                "[Jiachao] option %r not in %s", option, self._attr_options,
            )
            return

        idx = self._attr_options.index(option)

        if self._option_params is not None:
            params = self._option_params[idx]
            _LOGGER.debug("[Jiachao] select %s -> %s", option, params)
            await methods["select_option"](*params)
        elif self._option_values is not None:
            value = self._option_values[idx]
            await methods["select_option"](value)
        else:
            await methods["select_option"](idx)