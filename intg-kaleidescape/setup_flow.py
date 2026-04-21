"""
Kaleidescape integration setup and configuration flow.

Handles discovery, user selection, and device onboarding.

:copyright: (c) 2026 John J Carey
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

# pylint: disable=too-many-return-statements
# pylint: disable=too-many-branches
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=global-statement

from __future__ import annotations

import json
import logging
from typing import Any

import config
import ucapi
from api import api
from device import KaleidescapeInfo
from ksd_client import KsdClient

_LOG = logging.getLogger(__name__)

_DISCOVERED_BY_PLAYER_ID: dict[str, dict[str, str]] = {}
_backup_mode = False
_restore_mode = False
_client = KsdClient()


async def ksd_discover() -> list[dict[str, Any]]:
    """Fetch discovered systems from ksd."""
    resp = await _client.call_async({"cmd": "discover"})
    return resp.get("systems", [])

def _player_id(player: dict[str, str]) -> str:
    """Return a stable unique id for a discovered player."""
    return f'{player["player_serial"]}:{player["player_ip"]}'


def _flatten_players(systems: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Flatten discovered systems into selectable player records."""
    players: list[dict[str, str]] = []

    for system in systems:
        system_name = str(system.get("system_name", "") or "Kaleidescape")
        server_ip = str(system.get("server_ip", "") or "")

        for player in system.get("players", []):
            player_ip = str(player.get("player_ip", "") or "")
            player_serial = str(player.get("player_serial", "") or "")

            if not player_ip or not player_serial:
                continue

            item = {
                "system_name": system_name,
                "server_ip": server_ip,
                "player_ip": player_ip,
                "player_serial": player_serial,
                "zone_id": str(player.get("zone_id", 0)),
                "zone_name": str(player.get("zone_name", "") or f"Player {player_serial}"),
            }
            item["player_id"] = _player_id(item)
            players.append(item)

    players.sort(key=lambda p: (p["system_name"], p["zone_name"], p["player_ip"]))
    return players


def _select_player_form(players: list[dict[str, str]]) -> ucapi.RequestUserInput:
    """Dropdown of discovered players."""
    _DISCOVERED_BY_PLAYER_ID.clear()

    configured_ids = {d.id for d in config.devices if getattr(d, "id", None)}

    dropdown: list[dict[str, Any]] = []
    for player in players:
        if player["player_serial"] in configured_ids:
            continue

        pid = player["player_id"]
        _DISCOVERED_BY_PLAYER_ID[pid] = player

        label = f'{player["zone_name"]} ({player["system_name"]} - {player["player_ip"]})'
        dropdown.append({"id": pid, "label": {"en": label}})

    if not dropdown:
        return _reconfigure_menu_form(
            "No unconfigured Kaleidescape players were found."
        )

    return ucapi.RequestUserInput(
        {"en": "Select Kaleidescape Player"},
        [
            {
                "id": "info",
                "label": {"en": "Discovered Kaleidescape Players"},
                "field": {
                    "label": {
                        "value": {
                            "en": "Select the Kaleidescape player you want to configure."
                        }
                    }
                },
            },
            {
                "id": "selected_player_id",
                "label": {"en": "Player"},
                "field": {
                    "dropdown": {
                        "value": dropdown[0]["id"],
                        "items": dropdown,
                    }
                },
            },
        ],
    )


def _review_form(player: dict[str, str]) -> ucapi.RequestUserInput:
    """Review page before final setup."""
    return ucapi.RequestUserInput(
        {"en": "Review Kaleidescape Player"},
        [
            {
                "id": "info",
                "label": {"en": "Confirm player details"},
                "field": {
                    "label": {
                        "value": {
                            "en": (
                                "Confirm this is the Kaleidescape Player to configure. "
                                "These values are read-only and cannot be edited."
                            )
                        }
                    }
                },
            },
            {
                "id": "zone_name",
                "label": {"en": "Player Name:"},
                "field": {"text": {"value": player["zone_name"]}},
            },
            {
                "id": "player_ip",
                "label": {"en": "Player IP:"},
                "field": {"text": {"value": player["player_ip"]}},
            },
            {
                "id": "system_name",
                "label": {"en": "System Name:"},
                "field": {"text": {"value": player["system_name"]}},
            },
            {
                "id": "server_ip",
                "label": {"en": "Server IP:"},
                "field": {"text": {"value": player["server_ip"]}},
            },
        ],
    )


async def driver_setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """Main entry point."""
    if isinstance(msg, ucapi.DriverSetupRequest):
        return await handle_driver_setup(msg)

    if isinstance(msg, ucapi.UserDataResponse):
        return await handle_user_data_response(msg)

    if isinstance(msg, ucapi.AbortDriverSetup):
        _LOG.info("Setup aborted: %s", msg.error)
        _DISCOVERED_BY_PLAYER_ID.clear()
        global _restore_mode, _backup_mode
        _restore_mode = False
        _backup_mode = False
        return ucapi.SetupComplete()

    return ucapi.SetupError()


async def handle_driver_setup(msg: ucapi.DriverSetupRequest) -> ucapi.SetupAction:
    """Initial setup or reconfigure."""
    global _restore_mode, _backup_mode
    _restore_mode = False
    _backup_mode = False

    if msg.reconfigure:
        _DISCOVERED_BY_PLAYER_ID.clear()
        return _reconfigure_menu_form()

    api.available_entities.clear()
    api.configured_entities.clear()

    systems = await ksd_discover()
    players = _flatten_players(systems)

    if not players:
        return _reconfigure_menu_form(
            "No Kaleidescape players were found."
        )

    if len(players) > 1:
        return _select_player_form(players)

    player = players[0]
    _DISCOVERED_BY_PLAYER_ID.clear()
    _DISCOVERED_BY_PLAYER_ID[player["player_id"]] = player
    return _review_form(player)


async def handle_user_data_response(msg: ucapi.UserDataResponse) -> ucapi.SetupAction:
    """Handle user selections."""
    input_values = msg.input_values

    global _backup_mode

    if _backup_mode and "backup_data" in input_values:
        _backup_mode = False
        return ucapi.SetupComplete()

    restore_data = input_values.get("restore_data")
    if _restore_mode and restore_data is not None:
        return await _handle_restore_response(str(restore_data))

    selected_pid = input_values.get("selected_player_id")
    player_ip = input_values.get("player_ip")

    # Final submit from review page
    if player_ip:
        player = next(
            (p for p in _DISCOVERED_BY_PLAYER_ID.values() if p["player_ip"] == player_ip),
            None,
        )
        if player is None:
            return ucapi.SetupError()

        is_initial = (
            len(api.configured_entities.get_all()) == 0
            and len(api.available_entities.get_all()) == 0
        )

        if is_initial:
            config.devices.clear()

        info = KaleidescapeInfo(
            id=player["player_serial"],
            server_ip=player["server_ip"],
            friendly_name=player["zone_name"],
        )

        config.devices.add(info)
        _DISCOVERED_BY_PLAYER_ID.clear()
        return ucapi.SetupComplete()

    # Selection submit from discovered-player dropdown
    if selected_pid:
        player = _DISCOVERED_BY_PLAYER_ID.get(selected_pid)
        if player is None:
            return ucapi.SetupError()
        return _review_form(player)

    # Reconfigure menu submit only when we're actually on that form
    action = input_values.get("action")
    choice = input_values.get("choice")

    if action == "add":
        systems = await ksd_discover()
        players = _flatten_players(systems)

        if not players:
            return _reconfigure_menu_form(
                "No Kaleidescape players were found."
            )

        if len(players) > 1:
            return _select_player_form(players)

        player = players[0]
        _DISCOVERED_BY_PLAYER_ID.clear()
        _DISCOVERED_BY_PLAYER_ID[player["player_id"]] = player
        return _review_form(player)

    if action == "remove" and choice:
        config.devices.remove(choice)
        _DISCOVERED_BY_PLAYER_ID.clear()
        return ucapi.SetupComplete()

    if action == "reset":
        config.devices.clear()
        _DISCOVERED_BY_PLAYER_ID.clear()
        return ucapi.SetupComplete()

    if action == "backup":
        return await _handle_backup()

    if action == "restore":
        return await _handle_restore()

    return ucapi.SetupError()


def _reconfigure_menu_form(message: str | None = None) -> ucapi.RequestUserInput:
    """Reconfigure menu."""
    devices = [
        {"id": d.id, "label": {"en": d.friendly_name}}
        for d in config.devices
    ]

    actions = [{"id": "add", "label": {"en": "Add a new player"}}]

    if devices:
        actions += [
            {"id": "remove", "label": {"en": "Delete selected player"}},
            {"id": "reset", "label": {"en": "Remove ALL players"}},
            {"id": "backup", "label": {"en": "Backup configuration to clipboard"}},
            {"id": "restore", "label": {"en": "Restore configuration from backup"}},
        ]
    else:
        devices.append({"id": "", "label": {"en": "---"}})
        actions.append(
            {"id": "restore", "label": {"en": "Restore configuration from backup"}}
        )

    fields: list[dict[str, Any]] = []

    if message:
        fields.append(
            {
                "id": "info",
                "label": {"en": "Information"},
                "field": {
                    "label": {
                        "value": {"en": message}
                    }
                },
            }
        )

    fields.extend(
        [
            {
                "id": "choice",
                "label": {"en": "Configured players"},
                "field": {"dropdown": {"value": devices[0]["id"], "items": devices}},
            },
            {
                "id": "action",
                "label": {"en": "Action"},
                "field": {"dropdown": {"value": actions[0]["id"], "items": actions}},
            },
        ]
    )

    return ucapi.RequestUserInput({"en": "Configuration mode"}, fields)


async def _handle_backup() -> ucapi.RequestUserInput | ucapi.SetupError:
    """Show configuration backup data."""
    global _backup_mode
    _backup_mode = True

    try:
        backup_json = config.devices.get_backup_json()
        return ucapi.RequestUserInput(
            {"en": "Configuration Backup"},
            [
                {
                    "id": "info",
                    "label": {"en": "Configuration Backup"},
                    "field": {
                        "label": {
                            "value": {
                                "en": (
                                    "Copy the configuration data below and save it in a safe place. "
                                    "You can use it later to restore your configured players."
                                )
                            }
                        }
                    },
                },
                {
                    "id": "backup_data",
                    "label": {"en": "Configuration Data"},
                    "field": {"textarea": {"value": backup_json}},
                },
            ],
        )
    except Exception as err:  # pylint: disable=broad-except
        _LOG.error("Backup error: %s", err)
        return ucapi.SetupError()


async def _handle_restore() -> ucapi.RequestUserInput:
    """Show restore form."""
    global _restore_mode
    _restore_mode = True
    return await _build_restore_screen_with_error(None, "")


async def _build_restore_screen_with_error(
    error_message: str | None,
    restore_data: str,
) -> ucapi.RequestUserInput:
    """Build restore screen, optionally with an error message."""
    fields: list[dict[str, Any]] = []

    if error_message:
        fields.append(
            {
                "id": "error",
                "label": {"en": "Error"},
                "field": {
                    "label": {
                        "value": {"en": error_message}
                    }
                },
            }
        )

    fields.append(
        {
            "id": "info",
            "label": {"en": "Restore Configuration"},
            "field": {
                "label": {
                    "value": {
                        "en": "Paste the configuration backup data below to restore your configured players."
                    }
                }
            },
        }
    )

    fields.append(
        {
            "id": "restore_data",
            "label": {"en": "Configuration Backup Data"},
            "field": {"textarea": {"value": restore_data}},
        }
    )

    return ucapi.RequestUserInput({"en": "Restore Configuration"}, fields)


async def _handle_restore_response(
    restore_data: str,
) -> ucapi.SetupComplete | ucapi.SetupError | ucapi.RequestUserInput:
    """Handle restore form submission."""
    global _restore_mode, _backup_mode

    restore_data = restore_data.strip()

    if not restore_data:
        return await _build_restore_screen_with_error(
            "Please paste the configuration backup data.",
            restore_data,
        )

    try:
        data = json.loads(restore_data)
    except json.JSONDecodeError as err:
        return await _build_restore_screen_with_error(
            f"Invalid JSON format: {err.msg} at line {err.lineno}, column {err.colno}",
            restore_data,
        )

    if not config.devices.restore_from_backup(data):
        return await _build_restore_screen_with_error(
            "Invalid configuration backup data.",
            restore_data,
        )

    _restore_mode = False
    _backup_mode = False
    _DISCOVERED_BY_PLAYER_ID.clear()
    return ucapi.SetupComplete()
