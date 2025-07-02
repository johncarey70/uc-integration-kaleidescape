"""
Media-player entity functions.

:copyright: (c) 2023 by Unfolded Circle ApS.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import logging
from typing import Any

from const import MediaPlayerDef, SimpleCommands
from device import KaleidescapeInfo, KaleidescapePlayer
from ucapi import MediaPlayer, StatusCodes
from ucapi.media_player import (Attributes, Commands, DeviceClasses, Options,
                                States)

_LOG = logging.getLogger(__name__)

class KaleidescapeMediaPlayer(MediaPlayer):
    """Representation of a Kaleidescape Media Player entity."""

    def __init__(self, mp_info: KaleidescapeInfo, device: KaleidescapePlayer):
        """Initialize the class."""
        self._device = device
        entity_id = f"media_player.{mp_info.id}"
        features = MediaPlayerDef.features
        attributes = MediaPlayerDef.attributes
        #self.simple_commands = [*SimpleCommands]

        # options = {
        #     Options.SIMPLE_COMMANDS: self.simple_commands
        # }
        options = {}

        super().__init__(
            entity_id,
            f"{mp_info.friendly_name} Media Player",
            features,
            attributes,
            device_class=DeviceClasses.STREAMING_BOX,
            options=options,
        )

        _LOG.debug("KaleidescapeMediaPlayer init %s : %s", entity_id, attributes)

    async def command(self, cmd_id: str, params: dict[str, Any] | None = None) -> StatusCodes:
        """
        Media-player entity command handler.

        Called by the integration-API if a command is sent to a configured media-player entity.

        :param cmd_id: command
        :param params: optional command parameters
        :return: status code of the command request
        """
        _LOG.info("Got %s command request: %s %s", self.id, cmd_id, params)

        try:
            cmd = Commands(cmd_id)
        except ValueError:
            return StatusCodes.NOT_IMPLEMENTED

        match cmd:
            case Commands.ON:
                res = await self._device.power_on()
            case Commands.OFF:
                res = await self._device.power_off()
            case Commands.TOGGLE:
                res = await self._device.power_toggle()
            case Commands.PLAY_PAUSE:
                if self._device.is_on:
                    res = await self._device.play_pause()
                else:
                    return StatusCodes.OK
            case Commands.NEXT:
                res = await self._device.media_next_track()
            case Commands.PREVIOUS:
                res = await self._device.media_previous_track()
            case Commands.CURSOR_ENTER:
                res = await self._device.media_select()
            case Commands.STOP:
                res = await self._device.media_stop()
            case _:
                return StatusCodes.NOT_IMPLEMENTED

        return res

    def filter_changed_attributes(self, update: dict[str, Any]) -> dict[str, Any]:
        """
        Filter the given attributes and return only the changed values.

        :param update: dictionary with attributes.
        :return: filtered entity attributes containing changed attributes only.
        """
        attributes = {}

        for key in (
            Attributes.MEDIA_DURATION,
            Attributes.MEDIA_IMAGE_URL,
            Attributes.MEDIA_POSITION,
            Attributes.MEDIA_POSITION_UPDATED_AT,
            Attributes.MEDIA_TITLE,
            Attributes.MEDIA_TYPE,
            Attributes.STATE,
        ):
            if key in update and key in self.attributes:
                if update[key] != self.attributes[key]:
                    attributes[key] = update[key]

        if attributes.get(Attributes.STATE) == States.OFF:
            attributes[Attributes.SOURCE] = ""

        _LOG.debug("Kaleidescape MediaPlayer update attributes %s -> %s", update, attributes)
        return attributes
