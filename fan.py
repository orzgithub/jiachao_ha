"""Fan platform for Jiachao IoT."""
import logging

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import ordered_list_item_to_percentage

from .const import DOMAIN
from .hub import JiachaoHub
from .device_base import get_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up fans from config entry."""
    hub: JiachaoHub = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device in hub.devices.values():
        for spec in device.get_entity_specs():
            if spec["platform"] == "fan":
                entities.append(JiachaoFan(device, spec))
    async_add_entities(entities)


class JiachaoFan(FanEntity):
    """Generic fan entity driven by device spec."""

    _attr_has_entity_name = True

    def __init__(self, device, spec: dict) -> None:
        """Initialize fan entity."""
        self._device = device
        self._spec = spec

        self._attr_translation_key = spec["translation_key"]
        self._attr_unique_id = f"{device.device_id}_{spec['unique_id_suffix']}"
        self._attr_device_info = get_device_info(device)

        extra = spec.get("extra", {})
        self._preset_names = list(extra.get("preset_mode_names", []))
        self._preset_params = list(extra.get("preset_mode_params", []))
        self._attr_preset_modes = self._preset_names
        self._mode_key_getter = extra.get("mode_key_getter")

        self._attr_speed_count = extra.get("speed_count", 3)
        self._speed_list = extra.get("speed_list", ["1", "2", "3"])

        features = (
            FanEntityFeature.TURN_ON |
            FanEntityFeature.TURN_OFF |
            FanEntityFeature.SET_SPEED
        )
        methods = spec.get("methods", {})
        if "set_mode" in methods and self._preset_names:
            features |= FanEntityFeature.PRESET_MODE
        self._attr_supported_features = features

        device.register_callback(self._update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Clean up callback."""
        self._device.remove_callback(self._update_callback)

    @callback
    def _update_callback(self) -> None:
        """Schedule state update."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        power = self._device.state.get("power")
        return power == 1 if power is not None else False

    @property
    def percentage(self) -> int | None:
        """Return current speed percentage."""
        speed = self._device.state.get("speed")
        if speed is None:
            return None
        if 1 <= speed <= self._attr_speed_count:
            return ordered_list_item_to_percentage(
                self._speed_list, self._speed_list[speed - 1]
            )
        return None

    @property
    def preset_mode(self) -> str | None:
        """Return current preset mode key."""
        if self._mode_key_getter is None:
            return None
        return self._mode_key_getter()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs,
    ) -> None:
        """Turn the fan on."""
        methods = self._spec.get("methods", {})

        on_method = methods.get("turn_on")
        if on_method is not None:
            await on_method()

        if percentage is not None and percentage > 0:
            set_pct = methods.get("set_percentage")
            if set_pct is not None:
                speed = self._percentage_to_speed(percentage)
                await set_pct(speed)

        if preset_mode is not None:
            await self._apply_preset(preset_mode)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the fan off."""
        methods = self._spec.get("methods", {})
        off_method = methods.get("turn_off")
        if off_method is not None:
            await off_method()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set fan speed. If percentage is 0, turn off."""
        methods = self._spec.get("methods", {})

        if percentage == 0:
            off_method = methods.get("turn_off")
            if off_method is not None:
                await off_method()
            return

        if not self.is_on:
            on_method = methods.get("turn_on")
            if on_method is not None:
                await on_method()
                import asyncio
                await asyncio.sleep(1.0)

        set_pct = methods.get("set_percentage")
        if set_pct is not None:
            speed = self._percentage_to_speed(percentage)
            await set_pct(speed)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        if not self.is_on:
            methods = self._spec.get("methods", {})
            on_method = methods.get("turn_on")
            if on_method is not None:
                await on_method()
                import asyncio
                await asyncio.sleep(1.0)
        await self._apply_preset(preset_mode)

    async def _apply_preset(self, preset_mode: str) -> None:
        methods = self._spec.get("methods", {})
        set_mode = methods.get("set_mode")
        if set_mode is None:
            return

        if preset_mode not in self._preset_names:
            _LOGGER.warning(
                "[Jiachao] preset_mode %r not in %s",
                preset_mode, self._preset_names,
            )
            return

        idx = self._preset_names.index(preset_mode)
        params = self._preset_params[idx]
        _LOGGER.debug(
            "[Jiachao] preset_mode=%s -> set_mode%s", preset_mode, params,
        )
        await set_mode(*params)

    def _percentage_to_speed(self, percentage: int) -> int:
        """Convert percentage to integer speed (1-3)."""
        if percentage <= 33:
            return 1
        elif percentage <= 66:
            return 2
        else:
            return 3