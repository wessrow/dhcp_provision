#!/usr/bin/python3

"""
Device Detection helpers.
"""

import re
import sys
import logging
from .exceptions import UnsupportedOS

# pylint: disable=line-too-long

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout,
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )

class DeviceDetection:
    """
    Device Detection helpers.
    """

    def __init__(self, conn):
        """
        Constructor, make stuff available.
        """

        self.device_types = {
            "TEST": {
                "version_command": "blah",
                "configure_command": "blah",
                "interfaces_command": "blah"   
            },
            "ArubaOS-CX": {
                "os_slug": "aruba_aoscx",
                "version_command": "show version",
                "images_command": "show images",
                "system_command": "show system",
                "verify_os_regex": r"\bSHA-256\s+:\sVerifying\s([0-9]+%)\s+-",
                "os_regex": r"\bSHA-256\s+:\s(.+)\b",
                "download_os_command": [], #FIXME - Add command list.
                "reload_command": [("boot system", "Do you want to save the current configuration (y/n)?"),("n", "Continue (y/n)?"),("y", "")],
                "configure_command": "configure terminal",
                "interfaces_command": "show interface",
                "copy_config_command": "copy tftp://{tftp_server}/{serial}.conf {data_store}",
                "tftp_success_command": "Copying configuration: [Success]",
            }
        }

        self.conn = conn

    def match_device_os(self, show_version_command: str, regex_filter: str) -> bool:
        """
        Searches 'show version' command for supplied regex to find device OS.
        """

        result = self.conn.send_command(show_version_command)

        try:
            if regex_filter in re.search(r"" + re.escape(regex_filter) + r"", result.result).group(0):
                return True
            return False
        except AttributeError:
            logger.debug("%s was not found in the '%s' output.", regex_filter, show_version_command)
            return False

    def get_device_os(self) -> dict:
        """
        Goes through known DEVICE_TYPES and run 'show version' equivalent to get device OS.
        """

        for device_os, commands in self.device_types.items():

            if self.match_device_os(commands["version_command"], device_os):
                return self.device_types[device_os]

        raise UnsupportedOS

if __name__ == "__main__":

    pass
