#!/usr/bin/python3

"""
Functions to help with verifying OS
"""

import sys
import json
import logging
from scrapli.driver import GenericDriver

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout,
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )

class SFTPConnector:
    """
    SSH Device Connection-functions.
    """

    def __init__(self, host: str, auth_username: str, auth_password: str) -> None:
        """
        Constructor for the class. Connection is made available.
        """
        self.host = host
        self.device = GenericDriver(host=host,
                                    auth_username=auth_username,
                                    auth_password=auth_password,
                                    auth_strict_key=False,
                                    timeout_transport=0,
                                    timeout_ops=60
        )

        self.device.open()

    def load_os_json(self, os_info_file: str) -> dict:
        """
        Loads OS info data from SFTP-server. Returns dict.
        """

        result = self.device.send_command(f"cat {os_info_file}").result

        return json.loads(result)

    @staticmethod
    def compare_os_versions(device_os: str, desired_os: str) -> bool:
        """
        Compares device_os as desired_os hash to verify. Returns bool.
        """

        return bool(device_os == desired_os)

if __name__ == "__main__":

    # test = SFTPConnector(SFTP_SERVER)

    pass
