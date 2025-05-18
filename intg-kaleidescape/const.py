"""
Defines constant enumerations used for Kaleidescape remote and media player control.

Includes:
- `SimpleCommands`: Enum mapping human-readable command names to Kaleidescape-specific remote commands.
  Covers numeric inputs, aspect ratio changes, navigation, power control, and more.
- Designed for use with `ucapi`-based entity integration modules (e.g., remote, media_player).

These constants provide a unified interface for issuing commands across UC integrations.
"""


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

    DOWN = "down"
    EXIT = "exit"
    INPUT = "input"
    LEFT = "left"
    NEXT = "next"
    OK = "select"
    ON = "power_on"
    PAUSE = "pause"
    PLAY = "play"
    PLAY_PAUSE = "play_pause"
    PREV = "prev"
    RIGHT = "right"
    SAVE = "save"
    STBY = "standby"
    STOP = "stop"
    UP = "up"

class MediaPlayerDef: # pylint: disable=too-few-public-methods
    """
    Defines a media player entity including supported features, attributes, and
    a list of simple commands.
    """
    features = [
        media_player.Features.ON_OFF,
        media_player.Features.TOGGLE,
        media_player.Features.PLAY_PAUSE,
        media_player.Features.STOP,
        media_player.Features.NEXT,
        media_player.Features.PREVIOUS,
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
        remote.Attributes.STATE: remote.States.ON,
    }
    simple_commands = list(SimpleCommands)
