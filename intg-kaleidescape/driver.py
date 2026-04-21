#!/usr/bin/env python3
"""
Kaleidescape UC integration driver.

Coordinates device lifecycle, entity registration, and event handling.

:copyright: (c) 2026 John J Carey
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

# pylint: disable=too-many-branches

import asyncio
import logging
from typing import Any

import config
import ucapi
from api import api, loop
from device import Events, KaleidescapeInfo, KaleidescapePlayer
from ksd_client import KsdClient
from ksd_manager import start_ksd, start_ksd_services, stop_ksd_services
from media_player import KaleidescapeMediaPlayer
from registry import (all_devices, clear_devices, connect_all, disconnect_all,
                      get_device, register_device, unregister_device)
from remote import REMOTE_STATE_MAPPING, KaleidescapeRemote
from sensors import KaleidescapeSensor, build_kaleidescape_sensors
from setup_flow import driver_setup_handler
from ucapi.media_player import Attributes as MediaAttr
from ucapi.media_player import States
from ucapi.sensor import Attributes as SensorAttr
from utils import setup_logger

_LOG = logging.getLogger("driver")
_KSD_READY = asyncio.Event()
_KSD_START_LOCK = asyncio.Lock()

@api.listens_to(ucapi.Events.CONNECT)
async def on_connect() -> None:
    """Connect all configured receivers when the Remote Two sends the connect command."""
    _LOG.info("Received connect event message from remote")
    await api.set_device_state(ucapi.DeviceStates.CONNECTED)
    await _ensure_ksd_ready()
    loop.create_task(connect_all())


@api.listens_to(ucapi.Events.DISCONNECT)
async def on_r2_disconnect() -> None:
    """Disconnect notification from the Remote Two."""
    _LOG.info("Received disconnect event message from remote")
    await api.set_device_state(ucapi.DeviceStates.DISCONNECTED)
    loop.create_task(disconnect_all())


@api.listens_to(ucapi.Events.ENTER_STANDBY)
async def on_r2_enter_standby() -> None:
    """Enter standby notification from Remote Two."""
    _LOG.debug("Enter standby event: disconnecting device(s)")
    loop.create_task(disconnect_all())


@api.listens_to(ucapi.Events.EXIT_STANDBY)
async def on_r2_exit_standby() -> None:
    """Exit standby notification from Remote Two."""
    _LOG.debug("Exit standby event: connecting device(s)")
    await _ensure_ksd_ready()
    loop.create_task(connect_all())


@api.listens_to(ucapi.Events.SUBSCRIBE_ENTITIES)
async def on_subscribe_entities(entity_ids: list[str]) -> None:
    """Subscribe to given entities."""
    _LOG.debug("Subscribe entities event: %s", entity_ids)

    if not entity_ids:
        return

    first_entity = api.configured_entities.get(entity_ids[0])
    if not first_entity:
        _LOG.debug("Ignoring subscribe for stale entity %s (not configured)", entity_ids[0])
        return

    device_id = config.extract_device_id(first_entity)
    device = get_device(device_id)

    if not device:
        fallback_device = config.devices.get(device_id)
        if fallback_device:
            _configure_new_kaleidescape(fallback_device, connect=True)
            device = get_device(device_id)
            if not device:
                return
        else:
            _LOG.warning(
                "Failed to subscribe entities: No Kaleidescape configuration found for %s",
                device_id,
            )
            return


    for entity_id in entity_ids:
        entity = api.configured_entities.get(entity_id)
        if entity:
            _update_entity_attributes(entity_id, entity, device.attributes)


def _update_entity_attributes(entity_id: str, entity, attributes: dict) -> None:
    """Update attributes for the given entity based on its type."""
    _LOG.debug("Updating %s with %s", entity_id, attributes)

    if isinstance(entity, KaleidescapeMediaPlayer):
        api.configured_entities.update_attributes(entity_id, attributes)
    elif isinstance(entity, KaleidescapeRemote):
        api.configured_entities.update_attributes(
            entity_id,
            {
                ucapi.remote.Attributes.STATE: REMOTE_STATE_MAPPING.get(
                    attributes.get(MediaAttr.STATE, States.UNKNOWN)
                )
            },
        )
    elif isinstance(entity, KaleidescapeSensor):
        snapshot = entity.update_attributes(None) or {}
        if snapshot:
            merged = dict(entity.attributes or {})
            merged.update(snapshot)
            api.configured_entities.update_attributes(entity_id, merged)


@api.listens_to(ucapi.Events.UNSUBSCRIBE_ENTITIES)
async def on_unsubscribe_entities(entity_ids: list[str]) -> None:
    """On unsubscribe, disconnect devices only if no other entities are using them."""
    _LOG.debug("Unsubscribe entities event: %s", entity_ids)

    devices_to_remove = {
        config.extract_device_id(api.configured_entities.get(entity_id))
        for entity_id in entity_ids
        if api.configured_entities.get(entity_id)
    }

    remaining_entities = [
        e for e in api.configured_entities.get_all()
        if e.get("entity_id") not in entity_ids
    ]

    for entity in remaining_entities:
        device_id = config.extract_device_id(entity)
        devices_to_remove.discard(device_id)

    for device_id in devices_to_remove:
        device = get_device(device_id)
        if device is not None:
            await _async_remove_and_unregister(device_id, device)


def _configure_new_kaleidescape(info: KaleidescapeInfo, connect: bool = False) -> None:
    """Create and configure a new Kaleidescape device."""
    _LOG.debug("Configuring player %s (%s), connect=%s", info.friendly_name, info.id, connect)

    async def _reconfigure_existing_device(device: KaleidescapePlayer) -> None:
        await device.disconnect()
        if connect:
            await device.connect()

    device = get_device(info.id)
    if device:
        loop.create_task(_reconfigure_existing_device(device))
    else:
        device = KaleidescapePlayer(info)
        device.events.on(Events.CONNECTED.name, on_kaleidescape_connected)
        device.events.on(Events.DISCONNECTED.name, on_kaleidescape_disconnected)
        device.events.on(Events.UPDATE.name, on_kaleidescape_update)
        register_device(info.id, device)

        if connect:
            loop.create_task(device.connect())

    _register_available_entities(info, device)


def _register_available_entities(info: KaleidescapeInfo, device: KaleidescapePlayer) -> None:
    """Register remote, media player, and sensor entities for a Kaleidescape device."""
    def _add(entity) -> None:
        if api.available_entities.contains(entity.id):
            api.available_entities.remove(entity.id)
        api.available_entities.add(entity)

    for entity_cls in (KaleidescapeMediaPlayer, KaleidescapeRemote):
        _add(entity_cls(info, device))

    for entity in build_kaleidescape_sensors(info.id, info.friendly_name, device):
        _add(entity)


async def on_kaleidescape_connected(device_id: str) -> None:
    """Handle Kaleidescape connection events."""
    _LOG.debug("Kaleidescape connected: %s", device_id)
    await api.set_device_state(ucapi.DeviceStates.CONNECTED)


async def on_kaleidescape_disconnected(device_id: str) -> None:
    """Handle Kaleidescape disconnection events."""
    _LOG.debug("Kaleidescape disconnected: %s", device_id)

    any_connected = any(
        device is not None and getattr(device, "_connected", False)
        for device in all_devices().values()
    )

    await api.set_device_state(
        ucapi.DeviceStates.CONNECTED if any_connected else ucapi.DeviceStates.DISCONNECTED
    )


async def on_kaleidescape_update(entity_id: str, update: dict[str, Any] | None) -> None:
    """Update configured entity attributes when device attributes change."""
    if update is None:
        return

    device_id = entity_id.split(".", 1)[1]
    device = get_device(device_id)
    if device is None:
        return

    entity: (
        KaleidescapeMediaPlayer
        | KaleidescapeRemote
        | KaleidescapeSensor
        | None
    ) = api.configured_entities.get(entity_id)

    if entity is None:
        return

    if isinstance(entity, (KaleidescapeMediaPlayer, KaleidescapeRemote)):
        changed_attrs = entity.filter_changed_attributes(update)
    else:
        changed_attrs = entity.update_attributes(update) or {}

    if changed_attrs:
        loggable = {
            k: v for k, v in changed_attrs.items()
            if k != MediaAttr.MEDIA_POSITION
        }
        if loggable:
            _LOG.debug(
                "[%s] Applying changed attributes to %s: %s",
                device_id,
                entity_id,
                loggable,
            )

        merged = dict(entity.attributes or {})
        merged.update(changed_attrs)
        api.configured_entities.update_attributes(entity_id, merged)


def on_player_added(player_info: KaleidescapeInfo) -> None:
    """Handle a newly added player in the configuration."""
    _LOG.info("Adding Kaleidescape player %s (%s)", player_info.friendly_name, player_info.id)
    should_connect = api.device_state == ucapi.DeviceStates.CONNECTED
    _configure_new_kaleidescape(player_info, connect=should_connect)

    async def _sync_new_player() -> None:
        device = get_device(player_info.id)
        if device is None:
            return

        if should_connect and not getattr(device, "_connected", False):
            await device.connect()

    loop.create_task(_sync_new_player())


def _remove_kaleidescape_entities(device_id: str) -> None:
    """Remove all Kaleidescape entities for device_id from both configured and available."""
    suffix = f".{device_id}"
    _LOG.debug("_remove_kaleidescape_entities %s", device_id)

    for e in list(api.configured_entities.get_all()):
        eid = e.get("entity_id")
        if isinstance(eid, str) and eid.endswith(suffix):
            try:
                api.configured_entities.remove(eid)
            except (KeyError, ValueError, RuntimeError):
                pass

    for e in list(api.available_entities.get_all()):
        eid = e.get("entity_id")
        if isinstance(eid, str) and eid.endswith(suffix):
            try:
                api.available_entities.remove(eid)
            except (KeyError, ValueError, RuntimeError):
                pass

def on_player_removed(player_info: KaleidescapeInfo | None) -> None:
    """Handle removal of a Kaleidescape Player from config."""
    if player_info is None:
        _LOG.info("All devices cleared from config.")

        for device_id, device in list(all_devices().items()):
            for entity in list(api.configured_entities.get_all()):
                entity_id = entity.get("entity_id")
                if not isinstance(entity_id, str) or not entity_id.endswith(f".{device_id}"):
                    continue

                configured_entity = api.configured_entities.get(entity_id)
                if configured_entity is None:
                    continue

                if isinstance(configured_entity, KaleidescapeSensor):
                    api.configured_entities.update_attributes(
                        entity_id,
                        {
                            SensorAttr.STATE: ucapi.sensor.States.UNAVAILABLE,
                            SensorAttr.VALUE: "",
                        },
                    )
                else:
                    _update_entity_attributes(
                        entity_id,
                        configured_entity,
                        {MediaAttr.STATE: States.UNAVAILABLE},
                    )

            loop.create_task(_async_remove_and_unregister(device_id, device))
            _remove_kaleidescape_entities(device_id)

        api.configured_entities.clear()
        api.available_entities.clear()
        clear_devices()
        return

    _LOG.info("Removing Kaleidescape player %s (%s)", player_info.friendly_name, player_info.id)
    device_id = player_info.id

    for entity in list(api.configured_entities.get_all()):
        entity_id = entity.get("entity_id")
        if not isinstance(entity_id, str) or not entity_id.endswith(f".{device_id}"):
            continue

        configured_entity = api.configured_entities.get(entity_id)
        if configured_entity is None:
            continue

        if isinstance(configured_entity, KaleidescapeSensor):
            api.configured_entities.update_attributes(
                entity_id,
                {
                    SensorAttr.STATE: ucapi.sensor.States.UNAVAILABLE,
                    SensorAttr.VALUE: "",
                },
            )
        else:
            _update_entity_attributes(
                entity_id,
                configured_entity,
                {MediaAttr.STATE: States.UNAVAILABLE},
            )

    _remove_kaleidescape_entities(device_id)

    device = get_device(device_id)
    if device:
        loop.create_task(_async_remove_and_unregister(device_id, device))
    else:
        unregister_device(device_id)

    _LOG.info("Device for device_id %s cleaned up", device_id)


async def _async_remove_and_unregister(device_id: str, device: KaleidescapePlayer) -> None:
    """Disconnect device, remove listeners, then unregister it if still current."""
    _LOG.debug("[%s] Disconnecting and removing all listeners", device_id)
    await device.disconnect()
    device.events.remove_all_listeners()

    current = get_device(device_id)
    if current is device:
        unregister_device(device_id)
    else:
        _LOG.debug("[%s] Skipping unregister; device instance was replaced", device_id)


async def on_ksd_event(msg: dict[str, Any]) -> None:
    """Handle incoming events from the ksd daemon."""
    player_id = msg.get("player_id")
    if not isinstance(player_id, str):
        return

    device = get_device(player_id)
    if device is None:
        _LOG.debug("[event][unknown:%s] %s", player_id, msg)
        return

    await device.handle_event(msg)

async def _ensure_ksd_ready() -> None:
    """Ensure ksd is started and ready to serve requests."""
    if _KSD_READY.is_set():
        return

    async with _KSD_START_LOCK:
        if _KSD_READY.is_set():
            return

        client = KsdClient()
        await client.wait_until_ready()
        _KSD_READY.set()

async def _start_ksd_with_retry() -> None:
    """Start ksd with retry."""
    client = KsdClient()

    while True:
        try:
            _KSD_READY.clear()
            await start_ksd()
            await client.wait_until_ready()
            _KSD_READY.set()
            return
        except RuntimeError as err:
            _LOG.warning("ksd start failed, retrying: %s", err)
            await api.set_device_state(ucapi.DeviceStates.DISCONNECTED)
            await asyncio.sleep(5)

async def main():
    """Start the Remote Two integration driver."""
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)-14s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    setup_logger()

    _LOG.debug("Starting driver...")

    await api.init("driver.json", driver_setup_handler)

    config.devices = config.Devices(api.config_dir_path, on_player_added, on_player_removed)
    for device in config.devices:
        _configure_new_kaleidescape(device, connect=False)

    await _start_ksd_with_retry()
    await start_ksd_services(on_ksd_event)


if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(stop_ksd_services())
