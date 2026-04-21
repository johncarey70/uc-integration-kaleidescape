"""
Constants and enums for Kaleidescape UC integration.

Defines entity types, commands, and feature mappings.

:copyright: (c) 2026 John J Carey
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

from enum import Enum

from ucapi import media_player, remote
from ucapi.media_player import Commands


def format_command_label(cmd: str) -> str:
    """Convert a command id like 'cursor_up' to 'Cursor Up'."""
    return " ".join(part.capitalize() for part in cmd.split("_"))


class EntityPrefix(str, Enum):
    """Enumeration of entity prefixes."""

    MEDIA_PLAYER = "media_player"
    REMOTE = "remote"
    ASPECT_RATIO = "sensor_aspect_ratio"
    MOVIE_LOCATION = "sensor_movie_location"


class SimpleCommands(str, Enum):
    """Enumeration of supported remote command names for Kaleidescape control."""

    ALPHABETIZE_COVER_ART = "alphabetize_cover_art"
    BACK = "back"
    CANCEL = "cancel"
    DETAILS = "details"
    DOWN = "down"
    EXIT = "exit"
    INPUT = "input"
    INTERMISSION = "intermission"
    LEFT = "left"
    MENU = "menu"
    MOVIE_COLLECTIONS = "movie_collections"
    MOVIE_COVERS = "movie_covers"
    MOVIE_LIST = "movie_list"
    MOVIE_STORE = "movie_store"
    NEXT = "next"
    OK = "select"
    PAGE_DOWN = "page_down"
    PAGE_DOWN_PRESS = "page_down_press"
    PAGE_DOWN_RELEASE = "page_down_release"
    PAGE_UP = "page_up"
    PAGE_UP_PRESS = "page_up_press"
    PAGE_UP_RELEASE = "page_up_release"
    PAUSE = "pause"
    PLAY = "play"
    PLAY_PAUSE = "play_pause"
    PREVIOUS = "previous"
    REPLAY = "replay"
    RIGHT = "right"
    SAVE = "save"
    SCAN_FORWARD = "scan_forward"
    SCAN_REVERSE = "scan_reverse"
    SEARCH = "search"
    SHUFFLE_COVER_ART = "shuffle_cover_art"
    STOP = "stop"
    STOP_OR_CANCEL = "stop_or_cancel"
    SUBTITLES = "subtitles"
    UP = "up"

    @property
    def display_name(self) -> str:
        """Return a display-friendly command name."""
        if self.name == "PLAY_PAUSE":
            return "Play / Pause"

        return " ".join(part.capitalize() for part in self.name.lower().split("_"))


class MediaPlayerDef:  # pylint: disable=too-few-public-methods
    """
    Defines a media player entity including supported features, attributes, and
    a list of simple commands.
    """

    features = [
        media_player.Features.BROWSE_MEDIA,
        media_player.Features.CLEAR_PLAYLIST,
        media_player.Features.DPAD,
        media_player.Features.FAST_FORWARD,
        media_player.Features.GUIDE,
        media_player.Features.MEDIA_ALBUM,
        media_player.Features.MEDIA_ARTIST,
        media_player.Features.MEDIA_DURATION,
        media_player.Features.MEDIA_IMAGE_URL,
        media_player.Features.MEDIA_POSITION,
        media_player.Features.MEDIA_TITLE,
        media_player.Features.MEDIA_TYPE,
        media_player.Features.MENU,
        media_player.Features.NEXT,
        media_player.Features.ON_OFF,
        media_player.Features.PLAY_MEDIA,
        media_player.Features.PLAY_MEDIA_ACTION,
        media_player.Features.PLAY_PAUSE,
        media_player.Features.PREVIOUS,
        media_player.Features.REWIND,
        media_player.Features.SEARCH_MEDIA,
        media_player.Features.SEARCH_MEDIA_CLASSES,
        media_player.Features.SEEK,
        media_player.Features.STOP,
    ]

    attributes = {
        media_player.Attributes.MEDIA_DURATION: "",
        media_player.Attributes.MEDIA_IMAGE_URL: "",
        media_player.Attributes.MEDIA_POSITION: "",
        media_player.Attributes.MEDIA_POSITION_UPDATED_AT: "",
        media_player.Attributes.MEDIA_TITLE: "",
        media_player.Attributes.MEDIA_TYPE: "",
        media_player.Attributes.STATE: media_player.States.UNKNOWN,
    }

    simple_commands = sorted(
        {
            SimpleCommands.ALPHABETIZE_COVER_ART.display_name,
            SimpleCommands.CANCEL.display_name,
            SimpleCommands.DETAILS.display_name,
            SimpleCommands.INTERMISSION.display_name,
            SimpleCommands.MOVIE_COLLECTIONS.display_name,
            SimpleCommands.MOVIE_COVERS.display_name,
            SimpleCommands.MOVIE_LIST.display_name,
            SimpleCommands.MOVIE_STORE.display_name,
            SimpleCommands.PAGE_DOWN.display_name,
            SimpleCommands.PAGE_DOWN_PRESS.display_name,
            SimpleCommands.PAGE_DOWN_RELEASE.display_name,
            SimpleCommands.PAGE_UP.display_name,
            SimpleCommands.PAGE_UP_PRESS.display_name,
            SimpleCommands.PAGE_UP_RELEASE.display_name,
            SimpleCommands.REPLAY.display_name,
            SimpleCommands.SEARCH.display_name,
            SimpleCommands.SHUFFLE_COVER_ART.display_name,
            SimpleCommands.STOP_OR_CANCEL.display_name,
            SimpleCommands.SUBTITLES.display_name,
        }
    )


class RemoteDef:  # pylint: disable=too-few-public-methods
    """
    Defines a remote entity including supported features, attributes, and
    a list of simple commands.
    """

    features = [
        remote.Features.ON_OFF,
        remote.Features.SEND_CMD,
    ]
    attributes = {
        remote.Attributes.STATE: remote.States.UNKNOWN,
    }
    simple_commands = [cmd.display_name for cmd in SimpleCommands]
