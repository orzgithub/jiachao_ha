"""Base device class for Jiachao IoT."""
import asyncio
import json
import logging
import ssl
from typing import Any, Callable, Optional

import paho.mqtt.client as mqtt

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN, MQTT_SUB_TOPIC, MQTT_PUB_TOPIC

_LOGGER = logging.getLogger(__name__)

MAX_RETRY_DELAY = 300
INITIAL_RETRY_DELAY = 10


def get_device_info(device) -> dict[str, Any]:
    """Get device info dict for entity."""
    return {
        "identifiers": {(DOMAIN, device.device_id)},
        "name": device.alias or device.device_id,
        "manufacturer": "Jiachao",
        "model": "SAP Air Purifier" if device.__class__.__name__ == "JiachaoSAPDevice" else device.__class__.__name__,
        "sw_version": device.state.get("sw_version"),
        "hw_version": device.state.get("hw_version"),
    }


class JiachaoDeviceBase:
    """Base class for all Jiachao devices."""

    product_id: str = ""

    def __init__(
        self,
        hass: HomeAssistant,
        hub,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize device."""
        self.hass = hass
        self.hub = hub
        self.device_id = device_info["ID"]
        self.product_id = device_info.get("product_id", self.product_id)
        self.alias = device_info.get("alias", self.device_id)
        self.mqtt_domain = device_info["mqtt_domain"]
        self.mqtt_port = device_info.get("mqtt_port", 8883)
        self.mqtt_token = device_info["mqtt_token"]
        self.home_id = device_info.get("homeID")
        self.room_id = device_info.get("roomID")
        self.room_name = device_info.get("roomName", "")

        self._client: Optional[mqtt.Client] = None
        self._state: dict[str, Any] = {
            "online": True,
        }
        self._callbacks: list[Callable[[], None]] = []
        self._retry_unsub = None
        self._retry_count = 0
        self._intentional_disconnect = False

    @property
    def state(self) -> dict[str, Any]:
        """Return current state."""
        return self._state

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register update callback."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove update callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    @callback
    def _notify_update(self) -> None:
        """Notify all callbacks. Must be called on HA event loop."""
        for cb in self._callbacks:
            cb()

    async def async_start(self) -> None:
        """Start MQTT connection."""
        if self._client is not None:
            return

        self._intentional_disconnect = False

        username = self.hub.get_username(self.device_id)

        _LOGGER.info(
            "Connecting MQTT for device %s: host=%s:%s, username=%s",
            self.device_id, self.mqtt_domain, self.mqtt_port, username
        )

        client = mqtt.Client(
            client_id=f"ha-{self.device_id}",
            protocol=mqtt.MQTTv311,
        )
        client.username_pw_set(username, self.mqtt_token)
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message

        try:
            client.connect(self.mqtt_domain, self.mqtt_port, keepalive=60)
            client.loop_start()
            self._client = client
            self._retry_count = 0
            _LOGGER.info("MQTT connection initiated for device %s", self.device_id)
        except Exception as e:
            _LOGGER.error("Failed to connect MQTT for %s: %s", self.device_id, e)
            self._client = None
            self._schedule_retry()

    async def async_stop(self) -> None:
        """Stop MQTT connection."""
        self._intentional_disconnect = True
        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
        if self._retry_unsub is not None:
            self._retry_unsub()
            self._retry_unsub = None

    def _get_retry_delay(self) -> int:
        """Get retry delay with exponential backoff."""
        delay = min(
            INITIAL_RETRY_DELAY * (2 ** self._retry_count),
            MAX_RETRY_DELAY
        )
        return delay

    def _schedule_retry(self) -> None:
        """Schedule reconnect with exponential backoff."""
        if self._retry_unsub is not None:
            return

        delay = self._get_retry_delay()
        self._retry_count += 1
        _LOGGER.warning(
            "Scheduling MQTT reconnect for %s in %d seconds (attempt %d)",
            self.device_id, delay, self._retry_count
        )

        async def _retry(now):
            self._retry_unsub = None
            await self.async_start()

        self._retry_unsub = async_call_later(self.hass, delay, _retry)

    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connect. Runs in MQTT thread."""
        if rc == 0:
            _LOGGER.info("MQTT connected for device %s", self.device_id)
            self._retry_count = 0

            topic = MQTT_SUB_TOPIC.format(
                device_id=self.device_id,
                product_id=self.product_id,
            )
            _LOGGER.debug("Subscribing to topic: %s", topic)
            client.subscribe(topic)

            self._update_state_threadsafe({"online": True})

            self._send_command_sync({"m": {"req": {"a": "get_sap_stat"}}})
            self._send_command_sync({"m": {"req": {"a": "host_conf"}}})
        else:
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised",
            }
            error_msg = error_messages.get(rc, f"Unknown error code {rc}")
            _LOGGER.error(
                "MQTT connection failed for %s, rc=%d (%s)",
                self.device_id, rc, error_msg
            )
            self._update_state_threadsafe({"online": False})

            if rc in (4, 5):
                self.hass.loop.call_soon_threadsafe(
                    self._handle_auth_error
                )

    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnect. Runs in MQTT thread."""
        if self._intentional_disconnect:
            _LOGGER.debug("MQTT disconnected intentionally for %s", self.device_id)
            return

        _LOGGER.warning(
            "MQTT disconnected for %s, rc=%d",
            self.device_id, rc
        )
        self._update_state_threadsafe({"online": False})

        if self._client is client:
            self._client = None
            # Schedule retry
            self.hass.loop.call_soon_threadsafe(
                self._schedule_retry_threadsafe
            )

    @callback
    def _handle_auth_error(self) -> None:
        """Handle authentication error on HA event loop."""
        _LOGGER.warning(
            "Authentication error for %s. Token may be expired. "
            "Please re-add the integration to get a new token.",
            self.device_id
        )

    def _schedule_retry_threadsafe(self) -> None:
        """Schedule retry from HA loop."""
        if self._retry_unsub is None:
            self._schedule_retry()

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT message. Runs in MQTT thread."""
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            self.hass.loop.call_soon_threadsafe(
                self._process_payload_safe, payload
            )
        except json.JSONDecodeError:
            _LOGGER.debug(
                "Failed to decode JSON from %s: %s",
                self.device_id, msg.payload[:200]
            )
        except Exception as e:
            _LOGGER.debug("Error processing message from %s: %s", self.device_id, e)

    @callback
    def _process_payload_safe(self, payload: dict) -> None:
        """Process payload on HA event loop."""
        self._process_payload(payload)

    def _process_payload(self, payload: dict) -> None:
        """Process incoming MQTT message."""
        if "m" in payload and "res" in payload["m"]:
            res = payload["m"]["res"]
            if "a" in res:
                self.handle_response(res["a"], res)
        elif "deviceID" in payload and "msg" in payload:
            if payload["msg"] == "online":
                self.handle_response("online", {"param": payload.get("param", "1")})

    def _update_state_threadsafe(self, updates: dict) -> None:
        """Update state from MQTT thread."""
        @callback
        def _apply():
            self._state.update(updates)
            self._notify_update()

        try:
            self.hass.loop.call_soon_threadsafe(_apply)
        except Exception:
            pass

    def handle_response(self, action: str, data: dict) -> None:
        """Handle a response action. Override in subclass."""
        pass

    async def async_send_command(self, payload: dict) -> None:
        """Send MQTT command."""
        if self._client is None or not self._client.is_connected():
            _LOGGER.warning(
                "MQTT not connected for %s. Cannot send command: %s",
                self.device_id, payload
            )
            if self._client is None:
                await self.async_start()
            return

        topic = MQTT_PUB_TOPIC.format(
            device_id=self.device_id,
            product_id=self.product_id,
        )
        try:
            msg = json.dumps(payload)
            _LOGGER.debug("Sending to %s: %s", self.device_id, msg)
            self._client.publish(topic, msg)
        except Exception as e:
            _LOGGER.error("Failed to send command to %s: %s", self.device_id, e)

    def _send_command_sync(self, payload: dict) -> None:
        """Synchronous send. Can be called from MQTT thread."""
        if self._client and self._client.is_connected():
            topic = MQTT_PUB_TOPIC.format(
                device_id=self.device_id,
                product_id=self.product_id,
            )
            try:
                self._client.publish(topic, json.dumps(payload))
                _LOGGER.debug("Sent sync command to %s: %s", self.device_id, payload)
            except Exception as e:
                _LOGGER.error("Failed to send sync command to %s: %s", self.device_id, e)

    def get_entity_specs(self) -> list[dict[str, Any]]:
        """Return list of entity specifications for this device."""
        raise NotImplementedError