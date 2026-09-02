"""Config flow for Jiachao IoT."""
import logging
from typing import Any
import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_PHONE,
    CONF_COUNTRY_CODE,
    CONF_CODE,
    CONF_TOKEN,
    CONF_USER_ID,
    CONF_ZONE,
    CONF_DEVICES,
    API_SEND_CODE,
    API_LOGIN,
    API_DEVICE_LIST,
    API_HOME_LIST,
)

_LOGGER = logging.getLogger(__name__)


class JiachaoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jiachao IoT."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self.phone: str | None = None
        self.country_code: str = "+86"
        self.token: str | None = None
        self.user_id: str | None = None
        self.zone: str | None = None
        self.devices: list[dict[str, Any]] = []
        self.homes: list[dict[str, Any]] = []
        self.selected_home_id: int | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            self.phone = user_input[CONF_PHONE]
            self.country_code = user_input.get(CONF_COUNTRY_CODE, "+86")
            try:
                await self._send_code(self.phone, self.country_code)
                return await self.async_step_code()
            except Exception as e:
                _LOGGER.error("Failed to send code: %s", e)
                errors["base"] = "cannot_send_code"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PHONE): str,
                    vol.Optional(CONF_COUNTRY_CODE, default="+86"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_code(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step to input verification code."""
        errors = {}
        if user_input is not None:
            try:
                result = await self._login(
                    self.phone, self.country_code, user_input[CONF_CODE]
                )
                self.token = result["token"]
                self.user_id = str(result["userInfo"]["userId"])
                self.zone = result["userInfo"]["region"]

                await self._fetch_homes()

                if len(self.homes) == 1:
                    self.selected_home_id = self.homes[0]["homeID"]
                    await self._fetch_devices()
                    if self.devices:
                        return await self.async_step_devices()
                    else:
                        errors["base"] = "no_devices"
                elif len(self.homes) > 1:
                    return await self.async_step_home()
                else:
                    errors["base"] = "no_homes"
            except Exception as e:
                _LOGGER.error("Login failed: %s", e)
                errors["base"] = "invalid_code"

        return self.async_show_form(
            step_id="code",
            data_schema=vol.Schema({vol.Required(CONF_CODE): str}),
            errors=errors,
        )

    async def async_step_home(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select home if multiple."""
        errors = {}
        if user_input is not None:
            self.selected_home_id = user_input["home_id"]
            await self._fetch_devices()
            if self.devices:
                return await self.async_step_devices()
            else:
                errors["base"] = "no_devices"

        home_options = {
            home["homeID"]: home.get("homeName", f"Home {home['homeID']}")
            for home in self.homes
        }
        return self.async_show_form(
            step_id="home",
            data_schema=vol.Schema({vol.Required("home_id"): vol.In(home_options)}),
            errors=errors,
        )

    async def async_step_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Final step: confirm devices."""
        if user_input is not None:
            _LOGGER.info(
                "Creating config entry with %d devices for user %s",
                len(self.devices), self.user_id
            )
            return self.async_create_entry(
                title=f"Jiachao IoT ({self.phone})",
                data={
                    CONF_TOKEN: self.token,
                    CONF_USER_ID: self.user_id,
                    CONF_ZONE: self.zone,
                    CONF_DEVICES: self.devices,
                },
            )

        device_descriptions = []
        for d in self.devices:
            device_descriptions.append(
                f"- {d.get('alias', d['ID'])} ({d['dtype']})"
            )

        return self.async_show_form(
            step_id="devices",
            data_schema=vol.Schema({}),
            description_placeholders={
                "device_count": str(len(self.devices)),
                "devices": "\n".join(device_descriptions),
            },
        )

    async def _send_code(self, phone: str, country_code: str) -> None:
        """Send verification code."""
        session = async_get_clientsession(self.hass)
        async with session.get(
            API_SEND_CODE,
            params={
                "name": phone,
                "region": "CN",
                "lang": "zh",
                "countryCode": country_code,
            },
        ) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")
            await resp.json()

    async def _login(self, phone: str, country_code: str, code: str) -> dict:
        """Login with verification code."""
        session = async_get_clientsession(self.hass)
        params = {
            "name": phone,
            "code": code,
            "os": "android",
            "osVer": "unknown",
            "phoneBrand": "unknown",
            "pushToken": "",
            "uuid": "homeassistant",
            "lang": "zh",
            "appVer": "1.0.0",
            "app": "com.dc.jiachao",
        }
        async with session.get(API_LOGIN, params=params) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")
            data = await resp.json()
            if "token" not in data:
                _LOGGER.error("Login response missing token: %s", data)
                raise Exception("Invalid login response")
            return data

    async def _fetch_homes(self) -> None:
        """Fetch list of homes."""
        session = async_get_clientsession(self.hass)
        async with session.get(
            API_HOME_LIST,
            params={"token": self.token},
        ) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")
            self.homes = await resp.json()
            _LOGGER.info("Fetched %d homes", len(self.homes))

    async def _fetch_devices(self) -> None:
        """Fetch device list for selected home."""
        if self.selected_home_id is None:
            raise Exception("No home selected")

        session = async_get_clientsession(self.hass)
        async with session.get(
            API_DEVICE_LIST,
            params={
                "token": self.token,
                "homeDB": "CN",
                "homeID": self.selected_home_id,
            },
        ) as resp:
            if resp.status != 200:
                _LOGGER.error("Failed to fetch devices: HTTP %s", resp.status)
                raise Exception(f"HTTP {resp.status}")

            data = await resp.json()
            devices = data.get("list", [])

            for device in devices:
                dtype = device.get("dtype", "")
                match dtype:
                    case "SAP":
                        pass
                    case _:
                        _LOGGER.info("Skipping unsupported device type: %s", dtype)
                        continue

                mqtt_info = device.get("mqtt", {})
                if "token" not in mqtt_info or "domain" not in mqtt_info:
                    _LOGGER.warning(
                        "Device %s missing MQTT info, skipping",
                        device.get("ID", "unknown")
                    )
                    continue

                device_entry = {
                    "ID": device["ID"],
                    "product_id": device.get("product_id", "41"),
                    "alias": device.get("alias", device["ID"]),
                    "dtype": dtype,
                    "homeID": device.get("homeID"),
                    "roomID": device.get("roomID"),
                    "roomName": device.get("roomName", ""),
                    "mqtt_token": mqtt_info["token"],
                    "mqtt_domain": mqtt_info["domain"],
                    "mqtt_port": mqtt_info.get("port", 8883),
                }
                self.devices.append(device_entry)
                _LOGGER.info(
                    "Added device: %s (%s)",
                    device_entry["alias"], device_entry["ID"]
                )

            _LOGGER.info("Fetched %d SAP devices", len(self.devices))