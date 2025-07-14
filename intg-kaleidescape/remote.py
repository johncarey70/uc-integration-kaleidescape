"""
Remote entity functions.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from ucapi import StatusCodes
from ucapi.media_player import Attributes as MediaAttributes
from ucapi.media_player import States as MediaStates
from ucapi.remote import Attributes, Commands, EntityCommand, Remote, States
from ucapi.ui import (Buttons, DeviceButtonMapping, Size, UiPage,
                      create_btn_mapping, create_ui_text)

from const import RemoteDef
from const import SimpleCommands as cmds
from device import KaleidescapeInfo, KaleidescapePlayer

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
    "intermission",
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
            f"{info.friendly_name} Remote",
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
            create_btn_mapping(Buttons.DPAD_UP, cmds.UP),
            create_btn_mapping(Buttons.DPAD_DOWN, cmds.DOWN),
            create_btn_mapping(Buttons.DPAD_LEFT, cmds.LEFT),
            create_btn_mapping(Buttons.DPAD_RIGHT, cmds.RIGHT),
            create_btn_mapping(Buttons.DPAD_MIDDLE, cmds.OK),
            create_btn_mapping(Buttons.PREV, cmds.PREVIOUS),
            create_btn_mapping(Buttons.PLAY, cmds.PLAY_PAUSE),
            create_btn_mapping(Buttons.NEXT, cmds.NEXT),
            DeviceButtonMapping(
                button="MENU",
                short_press=EntityCommand(cmd_id=cmds.MENU_TOGGLE, params=None), long_press=None),
            DeviceButtonMapping(
                button="STOP",
                short_press=EntityCommand(cmd_id=cmds.STOP, params=None), long_press=None),
        ]

    def create_ui(self) -> list[UiPage | dict[str, Any]]:
        """Create a user interface with different pages that includes all commands"""

        ui_page1 = UiPage("page1", "Power", grid=Size(6, 6))
        ui_page1.add(create_ui_text("Power On", 0, 0, size=Size(3, 1), cmd=Commands.ON))
        ui_page1.add(create_ui_text("Standby", 3, 0, size=Size(3, 1), cmd=Commands.OFF))
        ui_page1.add(create_ui_text("Menu", 1, 1, size=Size(4, 1), cmd=cmds.MENU_TOGGLE))
        ui_page1.add(create_ui_text("-- Show Movie Views --", 1, 2, size=Size(4, 1)))
        ui_page1.add(create_ui_text("Collections", 0, 3, size=Size(2, 1), cmd=cmds.MOVIE_COLLECTIONS))
        ui_page1.add(create_ui_text("Covers", 2, 3, size=Size(2, 1), cmd=cmds.MOVIE_COVERS))
        ui_page1.add(create_ui_text("List", 4, 3, size=Size(2, 1), cmd=cmds.MOVIE_LIST))
        ui_page1.add(create_ui_text("Stop", 0, 4, size=Size(3, 1), cmd=cmds.STOP))
        ui_page1.add(create_ui_text("Cancel", 3, 4, size=Size(3, 1), cmd=cmds.CANCEL))
        ui_page1.add(create_ui_text("Intermission", 1, 5, size=Size(4, 1), cmd=cmds.INTERMISSION))
        return [ui_page1]

    async def command(self, cmd_id: str, params: dict[str, Any] | None = None) -> StatusCodes:
        """
        Handle command requests from the integration API for the media-player entity.

        :param cmd_id: Command identifier (e.g., "ON", "OFF", "TOGGLE", "SEND_CMD")
        :param params: Optional dictionary of parameters associated with the command
        :return: Status code indicating the result of the command execution
        """
        params = params or {}

        simple_cmd: str | None = params.get("command")
        if simple_cmd and simple_cmd.startswith("remote"):
            cmd_id = simple_cmd.split(".")[1]

        _LOG.info(
            "Received Remote command request: %s with parameters: %s",
            cmd_id, params or "no parameters")


        status = StatusCodes.BAD_REQUEST  # Default fallback

        try:
            cmd = Commands(cmd_id)
            _LOG.debug("Resolved command: %s", cmd)
        except ValueError:
            status = StatusCodes.NOT_IMPLEMENTED
        else:
            match cmd:
                case Commands.ON:
                    status = await self._device.power_on()

                case Commands.OFF:
                    status = await self._device.power_off()

                case Commands.SEND_CMD:
                    if not simple_cmd:
                        _LOG.warning("Missing command in SEND_CMD")
                        status = StatusCodes.BAD_REQUEST
                    else:
                        simple_cmd = normalize_cmd(simple_cmd)

                        match simple_cmd:
                            case cmds.INTERMISSION:
                                status = await self._device.intermission_toggle()
                            case cmds.MOVIE_COLLECTIONS:
                                status = await self._device.collections()
                            case cmds.MOVIE_COVERS:
                                status = await self._device.movie_covers()
                            case cmds.MOVIE_LIST:
                                status = await self._device.list()
                            case cmds.PLAY_PAUSE:
                                status = await self._device.play_pause()
                            case _:
                                status = await self._device.send_command(simple_cmd)

                case _:
                    status = StatusCodes.NOT_IMPLEMENTED

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

            try:
                media_state_enum = MediaStates(media_state)
            except ValueError:
                _LOG.warning("Unknown media_state value: %s", media_state)
                media_state_enum = MediaStates.UNKNOWN

            new_state: States = REMOTE_STATE_MAPPING.get(media_state_enum, States.UNKNOWN)
            current_state = self.attributes.get(Attributes.STATE)

            if current_state != new_state:
                attributes[Attributes.STATE] = new_state

        _LOG.debug("Kaleidescape Remote update attributes %s -> %s", update, attributes)
        return attributes

def normalize_cmd(cmd: str) -> str:
    return cmd.lower().replace(" / ", "_").replace(" ", "_").replace("ok", "select")

# def send_cmd(command: cmds):
#     """
#     Wraps a SimpleCommand enum into a UI-compatible send command payload.

#     :param command: A SimpleCommands enum member (e.g. SimpleCommands.UP).
#     :return: A dictionary payload compatible with remote.create_send_cmd().
#     """
#     return remote.create_send_cmd(command)
