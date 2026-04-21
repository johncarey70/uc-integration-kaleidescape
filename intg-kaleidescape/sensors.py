"""
Kaleidescape sensor entities.

:copyright:
    (c) 2026 John J Carey
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from config import KaleidescapeEntity
from const import EntityPrefix
from device import KaleidescapePlayer
from ucapi.media_player import States as MediaStates
from ucapi.sensor import Attributes as SensorAttr
from ucapi.sensor import DeviceClasses, Sensor, States
from utils import qualify_name

SENSOR_STATE_MAPPING: dict[MediaStates, States] = {
    MediaStates.OFF: States.UNAVAILABLE,
    MediaStates.ON: States.ON,
    MediaStates.STANDBY: States.ON,
    MediaStates.PLAYING: States.ON,
    MediaStates.PAUSED: States.ON,
    MediaStates.UNAVAILABLE: States.UNAVAILABLE,
    MediaStates.UNKNOWN: States.UNKNOWN,
}


MOVIE_LOCATION_LABELS: dict[str, str] = {
    "00": "Interface / Unknown",
    "01": "Unused",
    "02": "Unused",
    "03": "Main Content",
    "04": "Intermission",
    "05": "End Credits",
    "06": "Disc Menu",
}


def _normalize_movie_location(value: Any) -> str:
    if value is None:
        return ""

    code = str(value).strip()
    if not code:
        return ""

    if code.isdigit():
        code = code.zfill(2)

    return code


def _movie_location_sensor_value(device: KaleidescapePlayer) -> str:
    code = _normalize_movie_location(getattr(device, "movie_location", ""))
    if not code or code == "00":
        return ""

    return MOVIE_LOCATION_LABELS.get(code, "Unknown")


def _aspect_ratio_sensor_value(device: KaleidescapePlayer) -> str:
    return str(getattr(device, "aspect_ratio", "") or "")


@dataclass(frozen=True, slots=True)
class _SensorSpec:
    prefix: EntityPrefix
    name: str | dict[str, str]
    value_fn: Callable[[Any], str]
    device_class: DeviceClasses = DeviceClasses.CUSTOM


SENSOR_SPECS: dict[EntityPrefix, _SensorSpec] = {
    EntityPrefix.ASPECT_RATIO: _SensorSpec(
        prefix=EntityPrefix.ASPECT_RATIO,
        name={"en": "Aspect Ratio"},
        value_fn=_aspect_ratio_sensor_value,
    ),
    EntityPrefix.MOVIE_LOCATION: _SensorSpec(
        prefix=EntityPrefix.MOVIE_LOCATION,
        name={"en": "Movie Location"},
        value_fn=_movie_location_sensor_value,
    ),
}


class KaleidescapeSensor(Sensor, KaleidescapeEntity):
    """
    Generic Kaleidescape sensor driven by SENSOR_SPECS.

    Entity id convention: "{prefix}.{device_id}"
    """

    def __init__(
        self,
        device_id: str,
        device_name: str,
        device: KaleidescapePlayer,
        prefix: EntityPrefix,
    ) -> None:
        if prefix not in SENSOR_SPECS:
            raise ValueError(f"Unsupported sensor prefix: {prefix}")

        self.device_id = device_id
        self._device = device
        self._spec = SENSOR_SPECS[prefix]
        self._state: States = States.UNAVAILABLE

        entity_id = f"{self._spec.prefix.value}.{device_id}"
        qualified_name = qualify_name(device_name, self._spec.name)

        super().__init__(
            entity_id,
            qualified_name,
            [],
            {},
            device_class=self._spec.device_class,
        )

    @property
    def state(self) -> States:
        """Return current sensor state."""
        return self._state

    @property
    def sensor_value(self) -> str:
        """Return computed sensor value from device."""
        return self._spec.value_fn(self._device)

    def update_attributes(
        self,
        update: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Update or return sensor attributes."""
        if update:
            attrs: dict[str, Any] = {}

            if SensorAttr.STATE in update:
                if self._state != States.ON:
                    self._state = States.ON
                    attrs[SensorAttr.STATE] = self._state

            if SensorAttr.VALUE in update:
                attrs[SensorAttr.VALUE] = self.sensor_value

            return attrs or None

        self._state = States.ON

        return {
            SensorAttr.VALUE: self.sensor_value,
            SensorAttr.STATE: self._state,
        }


def build_kaleidescape_sensors(
    device_id: str,
    device_name: str,
    device: KaleidescapePlayer,
) -> list[KaleidescapeSensor]:
    """Build all Kaleidescape sensor entities for a device."""
    prefixes = [
        EntityPrefix.ASPECT_RATIO,
        EntityPrefix.MOVIE_LOCATION,
    ]
    return [KaleidescapeSensor(device_id, device_name, device, p) for p in prefixes]
