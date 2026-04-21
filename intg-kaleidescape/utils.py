"""
Utility helpers for Kaleidescape integration.

Includes logging setup and command normalization/validation.

:copyright: (c) 2026 John J Carey
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""


import logging
import os
from enum import Enum
from typing import Type


def setup_logger():
    """Get logger from all modules"""

    level = os.getenv("UC_LOG_LEVEL", "INFO").upper()
    ucapi_level = "WARNING"

    logging.getLogger("ucapi.api").setLevel(ucapi_level)
    logging.getLogger("ucapi.entities").setLevel(ucapi_level)
    logging.getLogger("ucapi.entity").setLevel(ucapi_level)
    logging.getLogger("driver").setLevel(level)
    logging.getLogger("config").setLevel(level)
    logging.getLogger("device").setLevel(level)
    logging.getLogger("remote").setLevel(level)
    logging.getLogger("media_player").setLevel(level)
    logging.getLogger("registry").setLevel(level)
    logging.getLogger("utils").setLevel(level)
    logging.getLogger("setup_flow").setLevel(level)




def validate_simple_commands_exist_on_executor(
    enum_class: Type[Enum],
    executor: object,
    logger: logging.Logger = logging.getLogger(__name__)
) -> list[str]:
    """
    Ensures that each command in the enum resolves to a callable method on the executor,
    using getattr(), which also triggers __getattr__ fallbacks.

    :param enum_class: Enum containing command names.
    :param executor: The CommandExecutor instance.
    :param logger: Logger for output.
    :return: List of commands that failed resolution.
    """
    missing = []

    for cmd in enum_class:
        method_name = cmd.value.lower()
        try:
            method = getattr(executor, method_name)
            if not callable(method):
                missing.append(method_name)
        except AttributeError:
            missing.append(method_name)

    if missing:
        logger.warning(
            "Executor missing methods for SimpleCommands: %s", ", ".join(missing)
        )
    else:
        logger.debug("All SimpleCommands are implemented by the executor.")

    return missing

def normalize_cmd(cmd: str) -> str:
    """Normalize the cmd"""
    return cmd.lower().replace(" / ", "_").replace(" ", "_").replace("ok", "select")

def qualify_name(device_name: str, base: str | dict[str, str]) -> str | dict[str, str]:
    if isinstance(base, dict):
        return {lang: f"{device_name} {txt}" for lang, txt in base.items()}
    return f"{device_name} {base}"
