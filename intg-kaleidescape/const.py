"""Defines constant enumerations used for Kaleidescape remote and media player control."""


from enum import Enum

from ucapi import media_player, remote


class EntityPrefix(str, Enum):
    """Enumeration of Sensors."""

    MEDIA_PLAYER = "media_player"
    REMOTE = "remote"

class SimpleCommands(str, Enum):
    """Enumeration of supported remote command names for Kaleidescape control."""

    CANCEL = "cancel"
    DOWN = "down"
    EXIT = "exit"
    INPUT = "input"
    INTERMISSION = "intermission"
    LEFT = "left"
    MENU = "menu_toggle"
    MOVIE_COLLECTIONS = "movie_collections"
    MOVIE_COVERS = "go_movie_covers"
    MOVIE_LIST = "movie_list"
    NEXT = "next"
    OK = "select"
    PAUSE = "pause"
    PLAY = "play"
    PLAY_PAUSE = "play_pause"
    PREVIOUS = "previous"
    REPLAY = "replay"
    RIGHT = "right"
    SAVE = "save"
    SCAN_FORWARD = "scan_forward"
    SCAN_REVERSE = "scan_reverse"
    SELECT = "select"
    STOP = "stop"
    UP = "up"


    @property
    def display_name(self) -> str:
        """
        Returns the display-friendly command name for use in UI or command APIs.

        Special cases like PLAY_PAUSE are formatted as "Play/Pause".

        :return: A display-safe string.
        """
        special_cases = {
            "PLAY_PAUSE": "Play / Pause",
        }

        if self.name in special_cases:
            return special_cases[self.name]

        parts = self.name.replace("_", " ").lower().split(maxsplit=1)
        return parts[0].capitalize() + (f" {parts[1].capitalize()}" if len(parts) > 1 else "")


class MediaPlayerDef: # pylint: disable=too-few-public-methods
    """
    Defines a media player entity including supported features, attributes, and
    a list of simple commands.
    """

    features = []
    attributes = {
    media_player.Attributes.MEDIA_DURATION: "",
    media_player.Attributes.MEDIA_IMAGE_URL: "",
    media_player.Attributes.MEDIA_POSITION: "",
    media_player.Attributes.MEDIA_POSITION_UPDATED_AT: "",
    media_player.Attributes.MEDIA_TITLE: "",
    media_player.Attributes.MEDIA_TYPE: "",
    media_player.Attributes.STATE: media_player.States.UNKNOWN,
}


class RemoteDef: # pylint: disable=too-few-public-methods
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
