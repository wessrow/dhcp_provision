#!/usr/bin/python3

"""
Helper functions to parse incoming webhook.
"""

import re
import sys
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout,
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )

def get_sender_hostname(data: str) -> str:
    """
    Parse originating devices' hostname from log.
    """

    try:
        return re.search(r'devname="?([^"]*)"?\s', data).group(1)
    except AttributeError:
        logger.error("No Sender Name")
        return None

def get_device_hostname(data: str) -> str:
    """
    Parse originating devices' hostname from log.
    """

    try:
        return re.search(r'hostname="?([^"]*)"?\s', data).group(1)
    except AttributeError:
        logger.error("No Device Name")
        return None


def get_ip_address(data: str) -> str:
    """
    Parse device-IP from log.
    """

    try:
        return re.search(r"(\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b)", data).group(0)
    except AttributeError:
        logger.error("No IP-Address")
        return None

def get_mac_address(data: str) -> str:
    """
    Parse device-mac from log.
    """

    try:
        return re.search(r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", data).group(0)
    except AttributeError:
        logger.error("No MAC-Address")
        return None

def parse_dhcp_log(data: str) -> dict:
    """
    Parse device-information from log. Returns dict
    """

    sender_hostname = get_sender_hostname(data)
    device_hostname = get_device_hostname(data)
    ip_address = get_ip_address(data)
    mac_address = get_mac_address(data)

    logger.info("%s handed out lease - MAC: %s - IP: %s - Client: %s", sender_hostname,
                                                                        mac_address,
                                                                        ip_address,
                                                                        device_hostname)

    if re.match(r"AP[-|_].*\b", device_hostname):
        logger.info("DHCP Client hostname contains 'AP-' - automation will not run.")
        return None

    return {"ip": ip_address, "mac": mac_address}

def parse_init_log(data: str) -> dict:
    """
    Parse BGP event.
    """

    sender_hostname = get_sender_hostname(data)

    try:
        re.search(r"VRF\s[0-9]\sneighbor\s((?:[0-9]{1,3}\.){3}[0-9]{1,3})\sUp", data).group(1)
    except AttributeError:
        logger.error("BGP Event was not 'Up'.")
        return None

    return {"hostname": sender_hostname}

if __name__ == "__main__":

    pass
