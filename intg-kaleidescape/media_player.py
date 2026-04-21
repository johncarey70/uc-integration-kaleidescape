"""
Kaleidescape media player entity implementation.

Handles playback commands, browsing, and state updates via ksd.

Derived from Unfolded Circle integration patterns.

:copyright:
    (c) 2023 Unfolded Circle ApS
    (c) 2026 John J Carey
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

# pylint: disable=too-many-statements
# pylint: disable=too-many-branches

import logging
from typing import Any

from const import MediaPlayerDef
from const import SimpleCommands as cmds
from device import KaleidescapeInfo, KaleidescapePlayer
from media_browser import KscapeMediaBrowser
from ucapi import MediaPlayer, StatusCodes, media_player
from ucapi.media_player import (Attributes, BrowseOptions, BrowseResults,
                                Commands, DeviceClasses, SearchOptions,
                                SearchResults, States)
from utils import normalize_cmd

_LOG = logging.getLogger(__name__)


class KaleidescapeMediaPlayer(MediaPlayer):
    """Representation of a Kaleidescape Media Player entity."""

    def __init__(self, mp_info: KaleidescapeInfo, device: KaleidescapePlayer):
        """Initialize the class."""
        self._device = device
        self._info = mp_info
        self.media_browser = KscapeMediaBrowser(self._info)

        entity_id = f"media_player.{mp_info.id}"
        features = MediaPlayerDef.features
        attributes = MediaPlayerDef.attributes
        options = {
            media_player.Options.SIMPLE_COMMANDS: MediaPlayerDef.simple_commands
        }

        super().__init__(
            entity_id,
            f"{mp_info.friendly_name} Media Player",
            features,
            attributes,
            device_class=DeviceClasses.STREAMING_BOX,
            options=options,
        )

        _LOG.debug("KaleidescapeMediaPlayer init %s : %s", entity_id, attributes)

    @staticmethod
    def _resolve_cmd(cmd_id: str) -> Commands | cmds | None:
        try:
            return Commands(cmd_id)
        except ValueError:
            pass
        try:
            return cmds(normalize_cmd(cmd_id))
        except ValueError:
            return None

    async def command(
        self,
        cmd_id: str,
        params: dict[str, Any] | None = None,
        *,
        websocket: Any,
    ) -> StatusCodes:
        """
        Media-player entity command handler.

        Called by the integration-API if a command is sent to a configured media-player entity.

        :param cmd_id: command
        :param params: optional command parameters
        :return: status code of the command request
        """
        del websocket

        _LOG.info("Got %s command request: %s %s", self.id, cmd_id, params)

        cmd = self._resolve_cmd(cmd_id)
        if cmd is None:
            return StatusCodes.NOT_IMPLEMENTED

        match cmd:
            case Commands.ON:
                res = await self._device.power_on()
            case Commands.OFF:
                res = await self._device.power_off()
            case Commands.PLAY_MEDIA:
                if not params or "media_id" not in params:
                    return StatusCodes.BAD_REQUEST
                res = await self._device.play_media(params["media_id"])
            case Commands.PLAY_PAUSE:
                res = await self._device.send_command("play_or_pause")
            case Commands.NEXT:
                res = await self._device.send_command("media_next_track")
            case Commands.PREVIOUS:
                res = await self._device.send_command("media_previous_track")
            case Commands.CURSOR_ENTER:
                res = await self._device.send_command("media_select")
            case Commands.BACK:
                res = await self._device.send_command("back")
            case Commands.CURSOR_UP:
                res = await self._device.send_command("cursor_up")
            case Commands.CURSOR_DOWN:
                res = await self._device.send_command("cursor_down")
            case Commands.CURSOR_LEFT:
                res = await self._device.send_command("cursor_left")
            case Commands.CURSOR_RIGHT:
                res = await self._device.send_command("cursor_right")
            case Commands.MENU:
                res = await self._device.send_command("menu")
            case Commands.FAST_FORWARD:
                res = await self._device.send_command("fast_forward")
            case Commands.REWIND:
                res = await self._device.send_command("rewind")
            case Commands.STOP:
                res = await self._device.send_command("media_stop")
            case cmds.ALPHABETIZE_COVER_ART:
                res = await self._device.send_command("alphabetize_cover_art")
            case cmds.CANCEL:
                res = await self._device.send_command("cancel")
            case cmds.DETAILS:
                res = await self._device.send_command("details")
            case cmds.INTERMISSION:
                res = await self._device.send_command("intermission_toggle")
            case cmds.MOVIE_COLLECTIONS:
                res = await self._device.send_command("collections")
            case cmds.MOVIE_COVERS:
                res = await self._device.send_command("movie_covers")
            case cmds.MOVIE_LIST:
                res = await self._device.send_command("list")
            case cmds.MOVIE_STORE:
                res = await self._device.send_command("movie_store")
            case cmds.PAGE_DOWN:
                res = await self._device.send_command("page_down")
            case cmds.PAGE_DOWN_PRESS:
                res = await self._device.send_command("page_down_press")
            case cmds.PAGE_DOWN_RELEASE:
                res = await self._device.send_command("page_down_release")
            case cmds.PAGE_UP:
                res = await self._device.send_command("page_up")
            case cmds.PAGE_UP_PRESS:
                res = await self._device.send_command("page_up_press")
            case cmds.PAGE_UP_RELEASE:
                res = await self._device.send_command("page_up_release")
            case cmds.REPLAY:
                res = await self._device.send_command("replay")
            case cmds.SEARCH:
                res = await self._device.send_command("search")
            case cmds.SHUFFLE_COVER_ART:
                res = await self._device.send_command("shuffle_cover_art")
            case cmds.STOP_OR_CANCEL:
                res = await self._device.send_command("stop_or_cancel")
            case cmds.SUBTITLES:
                res = await self._device.send_command("subtitles")
            case _:
                _LOG.debug("Not Implemented: %s", cmd)
                return StatusCodes.OK

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

        return attributes

    async def browse(self, options: BrowseOptions) -> BrowseResults | StatusCodes:
        """
        Browse media content.

        :param options: browse parameters
        :return: browse results or error status
        """

        browse_media_results, pagination = await self.media_browser.browse_media(
            options.media_id,
            options.media_type,
            options.paging,
        )

        return BrowseResults(media=browse_media_results, pagination=pagination)

    async def search(self, options: SearchOptions) -> SearchResults | StatusCodes:
        """
        Search media content.

        :param options: search parameters
        :return: search results or error status
        """

        if options.query is None:
            return StatusCodes.BAD_REQUEST

        media_results, pagination = await self.media_browser.search_media(
            options.query,
            options.media_id,
            options.media_type,
            options.filter,
            options.paging,
        )

        return SearchResults(media=media_results, pagination=pagination)
