"""
Remote entity functions.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from const import RemoteDef
from const import SimpleCommands as cmds
from player import KaleidescapeInfo, KaleidescapePlayer
from ucapi import StatusCodes
from ucapi.media_player import Attributes as MediaAttributes
from ucapi.media_player import States as MediaStates
from ucapi.remote import Attributes, Commands, Remote, States
from ucapi.ui import (Buttons, DeviceButtonMapping, Size, UiPage,
                      create_btn_mapping, create_ui_text)

_LOG = logging.getLogger(__name__)

REMOTE_STATE_MAPPING = {
    MediaStates.OFF: States.OFF,
    MediaStates.ON: States.ON,
    MediaStates.STANDBY: States.OFF,
    MediaStates.UNAVAILABLE: States.UNAVAILABLE,
    MediaStates.UNKNOWN: States.UNKNOWN,
}

VALID_COMMANDS = frozenset({
    "cancel",
    "down",
    "go_movie_covers",
    "left",
    "menu_toggle",
    "pause",
    "play",
    "play_pause",
    "replay",
    "right",
    "scan_forward",
    "scan_reverse",
    "select",
    "up",
})

class KaleidescapeRemote(Remote):
    """Representation of a Kaleidescape Remote entity."""

    def __init__(self, info: KaleidescapeInfo, device: KaleidescapePlayer):
        """Initialize the class."""
        self._device = device
        entity_id = f"remote.{info.id}"
        features = RemoteDef.features
        attributes = RemoteDef.attributes
        super().__init__(
            entity_id,
            info.friendly_name,
            features,
            attributes,
            simple_commands=RemoteDef.simple_commands,
            button_mapping=self.create_button_mappings(),
            ui_pages=self.create_ui()
        )


        _LOG.debug("KaleidescapeRemote init %s : %s", entity_id, attributes)

    def create_button_mappings(self) -> list[DeviceButtonMapping | dict[str, Any]]:
        """Create button mappings."""
        return [
            create_btn_mapping(Buttons.DPAD_UP, cmds.UP.value),
            create_btn_mapping(Buttons.DPAD_DOWN, cmds.DOWN.value),
            create_btn_mapping(Buttons.DPAD_LEFT, cmds.LEFT.value),
            create_btn_mapping(Buttons.DPAD_RIGHT, cmds.RIGHT.value),
            create_btn_mapping(Buttons.DPAD_MIDDLE, cmds.OK.value),
            create_btn_mapping(Buttons.PREV, cmds.PREV.value),
            create_btn_mapping(Buttons.PLAY, cmds.PLAY_PAUSE.value),
            create_btn_mapping(Buttons.NEXT, cmds.NEXT.value),

            {"button": "POWER", "short_press": {"cmd_id": "remote.toggle"}},
            {"button": "STOP", "short_press": {"cmd_id": "stop"}},
        ]

    def create_ui(self) -> list[UiPage | dict[str, Any]]:
        """Create a user interface with different pages that includes all commands"""

        ui_page1 = UiPage("page1", "Power", grid=Size(6, 6))
        ui_page1.add(create_ui_text("Power On", 2, 0, size=Size(6, 1), cmd=Commands.ON))
        ui_page1.add(create_ui_text("Standby", 0, 5, size=Size(6, 1), cmd=Commands.OFF))

        return [ui_page1]

    async def command(self, cmd_id: str, params: dict[str, Any] | None = None) -> StatusCodes:
        """
        Handle command requests from the integration API for the media-player entity.

        :param cmd_id: Command identifier (e.g., "ON", "OFF", "TOGGLE", "SEND_CMD")
        :param params: Optional dictionary of parameters associated with the command
        :return: Status code indicating the result of the command execution
        """
        if params is None:
            _LOG.info("Received Remote command request: %s - no parameters", cmd_id)
            params = {}
        else:
            _LOG.info("Received Remote command request: %s with parameters: %s", cmd_id, params)

        status = StatusCodes.BAD_REQUEST  # Default fallback

        try:
            cmd = Commands(cmd_id)
        except ValueError:
            return StatusCodes.NOT_IMPLEMENTED

        match cmd:
            case Commands.ON:
                _LOG.debug("Got On.............")
                try:
                    status = await self._device.power_on()
                except Exception as exc:
                    _LOG.error(exc)
                    status = StatusCodes.SERVER_ERROR

            case Commands.OFF:
                _LOG.debug("Got Off.............")
                status = await self._device.power_off()

            case Commands.TOGGLE:
                _LOG.debug("Got toggle.............")
                status = StatusCodes.OK

            case Commands.SEND_CMD:
                raw = params.get("command")
                if raw is None:
                    _LOG.warning("Missing 'command' parameter in SEND_CMD")
                    status = StatusCodes.BAD_REQUEST
                else:
                    try:
                        cmd = cmds(raw)
                        if cmd == cmds.PLAY_PAUSE:
                            status = await self._device.play_pause()
                        else:
                            status = await self._device.send_command(cmd.value)
                    except ValueError:
                        _LOG.warning("Invalid SEND_CMD command: %s", raw)
                        status = StatusCodes.BAD_REQUEST

        return status

    def filter_changed_attributes(self, update: dict[str, Any]) -> dict[str, Any]:
        """
        Filter the given media-player attributes and return remote attributes with converted state.

        :param update: dictionary with MediaAttributes.
        :return: dictionary with changed remote.Attributes only.
        """
        attributes = {}

        if MediaAttributes.STATE in update:
            media_state = update[MediaAttributes.STATE]

            new_state: States = REMOTE_STATE_MAPPING.get(media_state, States.UNKNOWN)

            # Check if the state has changed from the current remote state
            if Attributes.STATE not in self.attributes or self.attributes[Attributes.STATE] != new_state:
                attributes[Attributes.STATE] = new_state

        _LOG.debug("LumagenRemote update attributes %s -> %s", update, attributes)
        return attributes
