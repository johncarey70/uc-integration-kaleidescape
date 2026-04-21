"""
Public stub module.
"""

from dataclasses import dataclass
from enum import IntEnum


class Events(IntEnum):
    CONNECTED = 0
    DISCONNECTED = 1
    UPDATE = 2


@dataclass
class KaleidescapeInfo:
    id: str
    host_ip: str
    server_ip: str
    friendly_name: str


class KaleidescapePlayer:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("Backend not included in public repository")
