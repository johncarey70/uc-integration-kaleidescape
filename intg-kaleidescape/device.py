"""Provides connection utilities for communicating with a Kaleidescape Player."""

import asyncio
import json
import logging
import socket
from asyncio import AbstractEventLoop
from dataclasses import asdict, dataclass
from enum import IntEnum
from typing import Any

import ucapi
from const import EntityPrefix
from kaleidescape import Device as KaleidescapeDevice
from kaleidescape import KaleidescapeError
from kaleidescape.const import (DEVICE_POWER_STATE, DEVICE_POWER_STATE_ON,
                                DEVICE_POWER_STATE_STANDBY,
                                PLAY_STATUS_PLAYING, STATE_CONNECTED,
                                STATE_DISCONNECTED, STATE_RECONNECTING)
from pyee.asyncio import AsyncIOEventEmitter
from ucapi.media_player import Attributes as MediaAttr
from ucapi.media_player import States as MediaStates

#from ucapi.sensor import Attributes as SensorAttr

_LOG = logging.getLogger(__name__)

class Events(IntEnum):
    """Internal driver events."""

    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2
    ERROR = 3
    UPDATE = 4
    IP_ADDRESS_CHANGED = 5

class DeviceState:
    """
    Constants representing the possible states of a device connection.

    This class encapsulates connection state strings to provide a namespaced
    and safe way to reference them, especially in pattern matching constructs.

    Attributes:
        CONNECTED (str): Indicates the device is currently connected.
        DISCONNECTED (str): Indicates the device is currently disconnected.
        RECONNECTING (str): Indicates the device is attempting to reconnect.
    """
    CONNECTED = STATE_CONNECTED
    DISCONNECTED = STATE_DISCONNECTED
    RECONNECTING = STATE_RECONNECTING


@dataclass
class KaleidescapeInfo:
    """
    Represents a Kaleidescape Player discovered on the network.
    """
    id: str
    host: str
    location: str
    friendly_name: str
    manufacturer: str
    model_name: str
    serial_number: str

    def to_json(self, indent: int = 2, sort_keys: bool = True) -> str:
        """
        Return a JSON string representation of this device.
        :param indent: Indentation level for pretty-printing.
        :param sort_keys: Whether to sort keys alphabetically.
        :return: JSON string.
        """
        return json.dumps(asdict(self), indent=indent, sort_keys=sort_keys)

class KaleidescapePlayer:
    """Handles communication with a Kaleidescape Player over TCP."""

    def __init__(
        self,
        host: str,
        device_id: str | None = None,
        loop: AbstractEventLoop | None = None,
    ):
        # Identity and connection config
        self.device_id = device_id or "unknown"
        self.host = host
        self.device = KaleidescapeDevice(host, timeout=5, reconnect=True, reconnect_delay=5)

        # Event loop and internal connection state
        self._connected: bool = False
        self._event_loop = loop or asyncio.get_running_loop()
        self._attr_state = MediaStates.OFF

        # Device management and communication
        self.events = AsyncIOEventEmitter(self._event_loop)
        self.device.dispatcher.connect(self._on_event)

    @property
    def attributes(self) -> dict[str, any]:
        """Return the device attributes."""
        updated_data = {
            MediaAttr.STATE: self.state,
        }
        return updated_data

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self.device.power.state == DEVICE_POWER_STATE_ON

    @property
    def state(self) -> MediaStates:
        """Return the cached state of the device."""
        return self._attr_state

    async def connect(self) -> bool:
        """Establish a connection to the device."""
        _LOG.debug("Connecting to player")
        if self._connected:
            _LOG.debug("Already connected to Player at %s", self.host)
            return True

        self.events.emit(Events.CONNECTING.name, self.device_id)

        try:
            await self.device.connect()

        except (KaleidescapeError, ConnectionError) as err:
            await self.device.disconnect()
            _LOG.error("Unable to connect to %s: %s", self.host, err)
            return False

        return True

    async def disconnect(self):
        """Close the connection cleanly, if not already disconnecting."""
        _LOG.debug("Disconnecting from player")
        await self.device.disconnect()

    async def send_command(self, command: str) -> ucapi.StatusCodes:
        """Send a command to a device."""

        method = getattr(self.device, command, None)
        if not callable(method):
            _LOG.warning("Device method for command '%s' is not callable or missing", command)
            return ucapi.StatusCodes.NOT_FOUND

        _LOG.debug("Sending command: %s", command)
        await method()
        return ucapi.StatusCodes.OK

    async def power_on(self) -> ucapi.StatusCodes:
        """Turn the device on."""
        if self.is_on:
            self._log_power_state_skip("on")
        else:
            await self.device.leave_standby()
        return ucapi.StatusCodes.OK

    async def power_off(self) -> ucapi.StatusCodes:
        """Turn the device off."""
        if self.is_on:
            await self.device.enter_standby()
        else:
            self._log_power_state_skip("off")
        return ucapi.StatusCodes.OK

    def _log_power_state_skip(self, action: str):
        """Log when a power action is skipped because the device is already in the target state."""
        _LOG.debug("Power %s skipped: Device is already %s.", action, self.device.power.state)

    async def media_pause(self) -> ucapi.StatusCodes:
        """Send pause command."""
        await self.device.pause()
        return ucapi.StatusCodes.OK

    async def media_play(self) -> ucapi.StatusCodes:
        """Send play command."""
        await self.device.play()
        return ucapi.StatusCodes.OK

    async def media_stop(self) -> ucapi.StatusCodes:
        """Send stop command."""
        await self.device.stop()
        return ucapi.StatusCodes.OK

    async def media_next_track(self) -> ucapi.StatusCodes:
        """Send track next command."""
        await self.device.next()
        return ucapi.StatusCodes.OK

    async def media_previous_track(self) -> ucapi.StatusCodes:
        """Send track previous command."""
        await self.device.previous()
        return ucapi.StatusCodes.OK

    async def media_select(self) -> ucapi.StatusCodes:
        """Send select command."""
        await self.device.select()
        return ucapi.StatusCodes.OK

    async def play_pause(self) -> ucapi.StatusCodes:
        """Send Play-Pause command."""
        _LOG.debug("Play-Pause State = %s", self.device.movie.play_status)
        if self.device.movie.play_status == PLAY_STATUS_PLAYING:
            await self.media_pause()
        else:
            await self.media_play()
        return ucapi.StatusCodes.OK

    async def intermission_toggle(self) -> ucapi.StatusCodes:
        """Send intermission_toggle command."""
        message = "01/1/INTERMISSION_TOGGLE:\r"
        port = 10000
        timeout = 2  # seconds

        with socket.create_connection((self.host, port), timeout=timeout) as sock:
            sock.sendall(message.encode("utf-8"))

        return ucapi.StatusCodes.OK

    async def _on_event(self, event: str):
        """Handle device connection state changes based on incoming event."""
        if event == "":
            return
        _LOG.debug("Received Event: %s...........................", event)
        _LOG.debug("Power State = %s", self.state)
        handlers = {
            DEVICE_POWER_STATE: self._handle_power_state,
            DeviceState.CONNECTED: self._handle_connected,
            DeviceState.DISCONNECTED: self._handle_disconnected,
            DeviceState.RECONNECTING: self._handle_reconnecting,
        }

        handler = handlers.get(event, lambda: self._handle_events(event))
        await handler()

    async def _handle_connected(self):
        self._connected = True
        self.events.emit(Events.CONNECTED.name, self.device_id)

        await asyncio.sleep(1)

        if self.device.power.state == DEVICE_POWER_STATE_ON:
            self._attr_state = MediaStates.ON
        elif self.device.power.state == DEVICE_POWER_STATE_STANDBY:
            self._attr_state = MediaStates.STANDBY
        else:
            self._attr_state = MediaStates.UNKNOWN

        updates = {
                EntityPrefix.MEDIA_PLAYER: (MediaAttr.STATE, self.state),
                EntityPrefix.REMOTE: (MediaAttr.STATE, self.state),
            }

        for prefix, (attr, value) in updates.items():
            await self._emit_update(prefix.value, attr, value)

    async def _handle_disconnected(self):
        _LOG.debug("player disconnected")
        self._connected = False
        self._attr_state = MediaStates.UNAVAILABLE
        self.events.emit(Events.DISCONNECTED.name, self.device_id)

    async def _handle_reconnecting(self):
        _LOG.debug("player reconnecting")

    async def _handle_play_status(self):
        _LOG.debug("Player Status = %s", self.device.movie.play_status)

    async def _handle_power_state(self):
        _LOG.debug("Power State = %s", self.device.power.state)

        if self.device.power.state == DEVICE_POWER_STATE_ON:
            self._attr_state = MediaStates.ON
        elif self.device.power.state == DEVICE_POWER_STATE_STANDBY:
            self._attr_state = MediaStates.STANDBY
        else:
            self._attr_state = MediaStates.UNKNOWN

        await self._emit_update(
            EntityPrefix.MEDIA_PLAYER.value, MediaAttr.STATE, self.state)
        await self._emit_update(
            EntityPrefix.REMOTE.value, MediaAttr.STATE, self.state)

    async def _handle_events(self, event: str):
        _LOG.debug("Event received: %s", event)
        await self._emit_update(
            EntityPrefix.MEDIA_PLAYER.value, MediaAttr.STATE, self.state)
        await self._emit_update(
            EntityPrefix.REMOTE.value, MediaAttr.STATE, self.state)
        await self._emit_update(
            EntityPrefix.MEDIA_PLAYER.value, MediaAttr.MEDIA_IMAGE_URL, self.device.movie.cover)
        await self._emit_update(
            EntityPrefix.MEDIA_PLAYER.value, MediaAttr.MEDIA_TITLE, self.device.movie.title)
        await self._emit_update(
            EntityPrefix.MEDIA_PLAYER.value, MediaAttr.MEDIA_TYPE, self.device.movie.media_type)

    async def _emit_update(self, prefix: str, attr: str, value: Any) -> None:
        entity_id = f"{prefix}.{self.device_id}"
        self.events.emit(Events.UPDATE.name, entity_id, {attr: value})
