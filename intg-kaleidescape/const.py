"""Defines constant enumerations used for Kaleidescape remote and media player control."""


from enum import Enum

from ucapi import media_player, remote


class EntityPrefix(str, Enum):
    """Enumeration of Sensors."""

    MEDIA_PLAYER = "media_player"
    REMOTE = "remote"
    MEDIA_LOCATION = "media_location"
    PLAY_SPEED = "play_speed"
    PLAY_STATUS = "play_status"

class SimpleCommands(str, Enum):
    """Enumeration of supported remote command names for Kaleidescape control."""

    CANCEL = "cancel"
    DOWN = "down"
    EXIT = "exit"
    INPUT = "input"
    LEFT = "left"
    NEXT = "next"
    OK = "select"
    ON = "power_on"
    MENU = "menu_toggle"
    PAUSE = "pause"
    PLAY = "play"
    PLAY_PAUSE = "play_pause"
    PREVIOUS = "previous"
    REPLAY = "replay"
    RIGHT = "right"
    SAVE = "save"
    SELECT = "select"
    SCAN_FORWARD = "scan_forward"
    SCAN_REVERSE = "scan_reverse"
    STBY = "standby"
    STOP = "stop"
    UP = "up"
    INTERMISSION = "intermission"

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
    simple_commands = list(SimpleCommands)


class RemoteDef: # pylint: disable=too-few-public-methods
    """
    Defines a remote entity including supported features, attributes, and
    a list of simple commands.
    """
    features = [
        remote.Features.ON_OFF,
        remote.Features.TOGGLE,
        remote.Features.SEND_CMD,
    ]
    attributes = {
        remote.Attributes.STATE: remote.States.UNKNOWN,
    }
    simple_commands = list(SimpleCommands)
