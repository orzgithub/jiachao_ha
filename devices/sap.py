"""SAP Air Purifier device."""
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback

from ..device_base import JiachaoDeviceBase
from ..const import (
    CMD_SET_SAP_STAT,
    CMD_HOST_CONF,
    SAP_MODE_NAMES,
    SAP_MODE_PARAMS,
    SAP_SMODE_NAMES,
    SAP_SMODE_VALUES,
    SAP_LS_NAMES,
    SAP_LS_VALUES,
)

_LOGGER = logging.getLogger(__name__)


class JiachaoSAPDevice(JiachaoDeviceBase):
    """SAP Air Purifier device."""

    product_id = "41"

    def __init__(self, hass: HomeAssistant, hub, device_info: dict[str, Any]) -> None:
        """Initialize SAP device."""
        super().__init__(hass, hub, device_info)
        self._state.update({
            "power": None,
            "speed": None,
            "mode": None,
            "smode": None,
            "ls": None,
            "clock": None,
            "anion": None,
            "ve": None,
            "pm25": None,
            "ttime": None,
            "rtime": None,
            "mac": None,
            "sw_version": None,
            "hw_version": None,
            "ip": None,
        })

    @callback
    def handle_response(self, action: str, data: dict) -> None:
        """Handle SAP responses."""
        changed = False

        if action == "sap_stat":
            for key, state_key in [
                ("p", "power"), ("ws", "speed"), ("rm", "mode"),
                ("aqi_num", "pm25"), ("ttime", "ttime"), ("rtime", "rtime"),
            ]:
                if key in data:
                    self._state[state_key] = data[key]
                    changed = True

        elif action == "host_conf":
            for key, state_key in [
                ("smode", "smode"), ("ls", "ls"), ("clock", "clock"),
                ("anion", "anion"), ("ve", "ve"),
            ]:
                if key in data:
                    self._state[state_key] = data[key]
                    changed = True

        elif action == "aqi_value":
            if "aqi_num" in data:
                self._state["pm25"] = data["aqi_num"]
                changed = True

        elif action == "run_stat":
            if "ttime" in data:
                self._state["ttime"] = data["ttime"]
                changed = True

        elif action == "dev_conf":
            for key, state_key in [
                ("m", "mac"), ("w_v", "sw_version"),
                ("h_v", "hw_version"), ("ip", "ip"),
            ]:
                if key in data:
                    self._state[state_key] = data[key]
                    changed = True

        elif action == "online":
            if "param" in data:
                self._state["online"] = bool(int(data["param"]))
                changed = True

        if changed:
            self._notify_update()

    async def async_set_power_on(self) -> None:
        await self.async_send_command({
            "m": {"req": {"a": CMD_SET_SAP_STAT, "p": 1}}
        })

    async def async_set_power_off(self) -> None:
        await self.async_send_command({
            "m": {"req": {"a": CMD_SET_SAP_STAT, "p": 0}}
        })

    async def async_set_speed(self, speed: int) -> None:
        await self.async_send_command({
            "m": {"req": {"a": CMD_SET_SAP_STAT, "ws": speed}}
        })

    async def async_set_mode(self, rm: int, rtime: int | None = None) -> None:
        req = {"a": CMD_SET_SAP_STAT, "rm": rm}
        if rtime is not None:
            req["rtime"] = rtime
        await self.async_send_command({"m": {"req": req}})

    async def async_set_smode(self, smode: int) -> None:
        await self.async_send_command({
            "m": {"req": {"a": CMD_HOST_CONF, "smode": smode}}
        })

    async def async_set_ls(self, ls: int) -> None:
        await self.async_send_command({
            "m": {"req": {"a": CMD_HOST_CONF, "ls": ls}}
        })

    async def async_set_clock_on(self) -> None:
        await self.async_send_command({
            "m": {"req": {"a": CMD_HOST_CONF, "clock": 1}}
        })

    async def async_set_clock_off(self) -> None:
        await self.async_send_command({
            "m": {"req": {"a": CMD_HOST_CONF, "clock": 0}}
        })

    async def async_set_anion_on(self) -> None:
        await self.async_send_command({
            "m": {"req": {"a": CMD_HOST_CONF, "anion": 1}}
        })

    async def async_set_anion_off(self) -> None:
        await self.async_send_command({
            "m": {"req": {"a": CMD_HOST_CONF, "anion": 0}}
        })

    async def async_set_ve_on(self) -> None:
        await self.async_send_command({
            "m": {"req": {"a": CMD_HOST_CONF, "ve": 1}}
        })

    async def async_set_ve_off(self) -> None:
        await self.async_send_command({
            "m": {"req": {"a": CMD_HOST_CONF, "ve": 0}}
        })

    def _get_current_mode_key(self) -> str | None:
        rm = self._state.get("mode")
        rtime = self._state.get("rtime")
        if rm is None:
            return None
        if rm == 3:
            if rtime is not None and rtime > 0:
                return "pet"
            return "turbo"
        for (m_rm, _m_rtime), name in zip(SAP_MODE_PARAMS, SAP_MODE_NAMES):
            if m_rm == rm and m_rm != 3:
                return name
        return None

    def get_entity_specs(self) -> list[dict[str, Any]]:
        """Return entity specs for SAP device."""
        return [
            {
                "platform": "fan",
                "translation_key": "air_purifier",
                "unique_id_suffix": "fan",
                "methods": {
                    "turn_on": self.async_set_power_on,
                    "turn_off": self.async_set_power_off,
                    "set_percentage": self.async_set_speed,
                    "set_mode": self.async_set_mode,   # ← 接收 (rm, rtime)
                },
                "extra": {
                    "preset_mode_names": SAP_MODE_NAMES,
                    "preset_mode_params": SAP_MODE_PARAMS,
                    "speed_count": 3,
                    "speed_list": ["1", "2", "3"],
                    "mode_key_getter": self._get_current_mode_key,
                },
            },
            {
                "platform": "select",
                "translation_key": "mode",
                "unique_id_suffix": "mode",
                "methods": {"select_option": self.async_set_mode},
                "extra": {
                    "options": SAP_MODE_NAMES,
                    "option_params": SAP_MODE_PARAMS,
                    "mode_key_getter": self._get_current_mode_key,
                },
            },
            {
                "platform": "select",
                "translation_key": "startup_mode",
                "unique_id_suffix": "smode",
                "methods": {"select_option": self.async_set_smode},
                "extra": {
                    "options": SAP_SMODE_NAMES,
                    "option_values": SAP_SMODE_VALUES,
                    "value_getter": lambda: self.state.get("smode"),
                },
            },
            {
                "platform": "select",
                "translation_key": "indicator_light",
                "unique_id_suffix": "ls",
                "methods": {"select_option": self.async_set_ls},
                "extra": {
                    "options": SAP_LS_NAMES,
                    "option_values": SAP_LS_VALUES,
                    "value_getter": lambda: self.state.get("ls"),
                },
            },
            {
                "platform": "switch",
                "translation_key": "child_lock",
                "unique_id_suffix": "clock",
                "methods": {
                    "turn_on": self.async_set_clock_on,
                    "turn_off": self.async_set_clock_off,
                },
                "extra": {
                    "value_getter": lambda: bool(self.state.get("clock")) if self.state.get("clock") is not None else None,
                    "icon": "mdi:lock",
                },
            },
            {
                "platform": "switch",
                "translation_key": "anion",
                "unique_id_suffix": "anion",
                "methods": {
                    "turn_on": self.async_set_anion_on,
                    "turn_off": self.async_set_anion_off,
                },
                "extra": {
                    "value_getter": lambda: bool(self.state.get("anion")) if self.state.get("anion") is not None else None,
                    "icon": "mdi:creation",
                },
            },
            {
                "platform": "switch",
                "translation_key": "button_sound",
                "unique_id_suffix": "ve",
                "methods": {
                    "turn_on": self.async_set_ve_on,
                    "turn_off": self.async_set_ve_off,
                },
                "extra": {
                    "value_getter": lambda: bool(self.state.get("ve")) if self.state.get("ve") is not None else None,
                    "icon": "mdi:volume-high",
                },
            },
            {
                "platform": "sensor",
                "translation_key": "pm25",
                "unique_id_suffix": "pm25",
                "extra": {
                    "device_class": "pm25",
                    "state_class": "measurement",
                    "unit": "µg/m³",
                    "precision": 0,
                    "value_getter": lambda: self.state.get("pm25"),
                    "icon": "mdi:air-filter",
                },
            },
            {
                "platform": "sensor",
                "translation_key": "runtime",
                "unique_id_suffix": "runtime",
                "extra": {
                    "device_class": None,
                    "state_class": "total_increasing",
                    "unit": "min",
                    "value_getter": lambda: self.state.get("ttime"),
                    "icon": "mdi:timer-outline",
                },
            },
        ]