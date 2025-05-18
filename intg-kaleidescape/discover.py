"""
Kaleidescape SSDP discovery module.

Discovers Kaleidescape players (e.g., Strato, Alto) on the local network using UPnP/SSDP.
"""

import asyncio
import logging
import random
import select
import socket
import time
import xml.etree.ElementTree as ET

import requests
from player import KaleidescapeInfo

_LOG = logging.getLogger(__name__)


class SSDPDiscovery:
    """
    SSDP discovery client for locating UPnP devices on the local network.
    This class supports early exit when a Kaleidescape player is found.
    """

    MCAST_GRP = "239.255.255.250"
    MCAST_PORT = 1900
    M_SEARCH_MSG = (
        "M-SEARCH * HTTP/1.1\r\n"
        "HOST: 239.255.255.250:1900\r\n"
        "MAN: \"ssdp:discover\"\r\n"
        "MX: 1\r\n"
        "ST: ssdp:all\r\n"
        "\r\n"
    )

    def __init__(self, timeout: float = 2.0):
        """
        :param timeout: Maximum time in seconds to wait for SSDP responses.
        """
        self.timeout = timeout

    def discover_first(self) -> dict | None:
        """
        Discover the first Kaleidescape player found via SSDP.

        :return: A dictionary with device information, or None if not found.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(0.1)
        sock.sendto(self.M_SEARCH_MSG.encode("utf-8"), (self.MCAST_GRP, self.MCAST_PORT))

        start_time = time.time()
        seen_locations = set()

        while time.time() - start_time < self.timeout:
            ready = select.select([sock], [], [], 0.3)
            if ready[0]:
                try:
                    data, addr = sock.recvfrom(1024)
                    parsed = self.parse_ssdp_response(data.decode("utf-8", errors="ignore"))
                    parsed["address"] = addr[0]

                    location = parsed.get("LOCATION")
                    if not location or location in seen_locations:
                        continue

                    if is_kaleidescape_device(parsed):
                        _LOG.debug("Candidate device at %s: %s", addr[0], location)
                        seen_locations.add(location)
                        info = fetch_device_info(location)
                        if is_kaleidescape_player(info):
                            _LOG.info("Kaleidescape player found at %s", addr[0])
                            sock.close()
                            return KaleidescapeInfo(
                                id=info.get("serialNumber", "").replace(" ", ""),
                                host=parsed["address"],
                                location=location,
                                friendly_name=info.get("friendlyName", ""),
                                manufacturer=info.get("manufacturer", ""),
                                model_name=info.get("modelName", ""),
                                serial_number=info.get("serialNumber", ""),
                            )

                        _LOG.debug("Ignored non-player device at %s", addr[0])
                except (socket.timeout, UnicodeDecodeError, ValueError) as exc:
                    _LOG.debug("SSDP recv/parse error: %s", exc)

        sock.close()
        _LOG.debug("SSDP discovery timed out with no match.")
        return None

    @staticmethod
    def parse_ssdp_response(data: str) -> dict:
        """
        Parse SSDP response headers.
        :param data: Raw HTTP-like SSDP response.
        :return: Dictionary of headers.
        """
        headers = {}
        lines = data.split("\r\n")
        for line in lines[1:]:
            if ":" in line:
                h_key, h_val = line.split(":", 1)
                headers[h_key.strip().upper()] = h_val.strip()
        return headers


def is_kaleidescape_device(response: dict) -> bool:
    """
    Identify if SSDP response is from a Kaleidescape device.

    :param response: Parsed SSDP response headers.
    :return: True if device is a Kaleidescape unit.
    """
    server = response.get("SERVER", "").lower()
    return any(x in server for x in ["kaleidescape", "kos/", "kdiscoveryd"])


def is_kaleidescape_player(info: dict) -> bool:
    """
    Determine if the device info belongs to a Kaleidescape player (not a server).

    :param info: Parsed XML device metadata.
    :return: True if device is a player.
    """
    model = info.get("modelName", "").lower()
    name = info.get("friendlyName", "").lower()
    combined = f"{model} {name}"
    return any(keyword in combined for keyword in ["strato", "alto", "player"])


def fetch_device_info(description_url: str) -> dict:
    """
    Fetch and parse device metadata from a UPnP description.xml endpoint.

    :param description_url: URL to the UPnP XML descriptor.
    :return: Dictionary with parsed device fields.
    """
    try:
        response = requests.get(description_url, timeout=3)
        if response.status_code != 200:
            return {}

        xml_root = ET.fromstring(response.content)
        device_elem = xml_root.find(".//{urn:schemas-upnp-org:device-1-0}device")
        if device_elem is None:
            return {}

        return {
            "friendlyName": device_elem.findtext("{urn:schemas-upnp-org:device-1-0}friendlyName"),
            "manufacturer": device_elem.findtext("{urn:schemas-upnp-org:device-1-0}manufacturer"),
            "modelName": device_elem.findtext("{urn:schemas-upnp-org:device-1-0}modelName"),
            "serialNumber": device_elem.findtext("{urn:schemas-upnp-org:device-1-0}serialNumber"),
        }
    except (requests.RequestException, ET.ParseError) as exc:
        _LOG.debug("Failed to fetch or parse device info: %s", exc)
        return {}


async def discover_kaleidescape_device(timeout: float = 2.0, retries: int = 2) -> dict | None:
    """
    Asynchronously discover the first available Kaleidescape player on the network.

    Retries the SSDP discovery if the player is not found on the first attempt.

    :param timeout: How long to wait for SSDP responses per attempt (in seconds)
    :param retries: Number of discovery attempts before giving up
    :return: A dictionary of device info or None if no player found
    """
    for attempt in range(retries):
        _LOG.debug("Discovery attempt %d of %d", attempt + 1, retries)
        result = await asyncio.to_thread(SSDPDiscovery(timeout).discover_first)
        if result:
            return result
        if attempt < retries - 1:
            await asyncio.sleep(random.uniform(0.1, 0.3))
    return None


async def main():
    """
    Asynchronously run discovery and print the first Kaleidescape player found.
    """
    logging.basicConfig(level=logging.INFO)

    device = await discover_kaleidescape_device()
    if device:
        _LOG.info("Kaleidescape Player Found:")
        print(device)
    else:
        _LOG.warning("No Kaleidescape player found.")

if __name__ == "__main__":
    asyncio.run(main())
