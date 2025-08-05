"""Defines constant enumerations used for Kaleidescape remote and media player control."""


from enum import Enum

from ucapi import media_player, remote


class EntityPrefix(str, Enum):
    """Enumeration of Sensors."""

    MEDIA_PLAYER = "media_player"
    REMOTE = "remote"

class SimpleCommands(str, Enum):
    """Enumeration of supported remote command names for Kaleidescape control."""

    ALPHABETIZE_COVER_ART = "alphabetize_cover_art"
    BACK = "back"
    CANCEL = "cancel"
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
    PAUSE = "pause"
    PLAY = "play"
    PLAY_PAUSE = "play_pause"
    PREVIOUS = "previous"
    REPLAY = "replay"
    RIGHT = "right"
    SAVE = "save"
    SCAN_FORWARD = "scan_forward"
    SCAN_REVERSE = "scan_reverse"
    SHUFFLE_COVER_ART = "shuffle_cover_art"
    SUBTITLES = "subtitles"
    STOP = "stop"
    UP = "up"


    @property
    def display_name(self) -> str:
        """
        Returns the display-friendly command name for use in UI or command APIs.

        Special cases like PLAY_PAUSE are formatted as "Play / Pause".

        :return: A display-safe string.
        """
        special_cases = {
            "PLAY_PAUSE": "Play / Pause",
        }

        if self.name in special_cases:
            return special_cases[self.name]

        return " ".join(part.capitalize() for part in self.name.lower().split("_"))


class MediaPlayerDef: # pylint: disable=too-few-public-methods
    """
    Defines a media player entity including supported features, attributes, and
    a list of simple commands.
    """

    features = [
        media_player.Features.ON_OFF,
        media_player.Features.VOLUME_UP_DOWN,
        media_player.Features.MUTE_TOGGLE,
        media_player.Features.PLAY_PAUSE,
        media_player.Features.STOP,
        media_player.Features.NEXT,
        media_player.Features.PREVIOUS,
        media_player.Features.MEDIA_DURATION,
        media_player.Features.MEDIA_POSITION,
        media_player.Features.MEDIA_TITLE,
        media_player.Features.MEDIA_ARTIST,
        media_player.Features.MEDIA_ALBUM,
        media_player.Features.MEDIA_IMAGE_URL,
        media_player.Features.MEDIA_TYPE,
        media_player.Features.HOME,
        media_player.Features.DPAD,
        media_player.Features.MENU,
        media_player.Features.REWIND,
        media_player.Features.FAST_FORWARD,
        media_player.Features.SEEK,
        media_player.Features.GUIDE,
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
