#!/usr/bin/python3

"""
Custom exceptions
"""

# pylint: disable=line-too-long

class DeviceNotFound(Exception):
    "Raised when no device was found with matching serial"
    def __init__(self, serial: str, message: str = "No Netbox device matching serial") -> None:
        self.serial = serial
        self.message = f"{message} '{serial}'"
        super().__init__(self.message)

class UnsupportedOS(Exception):
    "Raised when no matching device OS was found"
    def __init__(self, host: str = None, message: str = "No supported OS matched device output.") -> None:
        self.host = host
        self.message = f"{host} - {message}"
        super().__init__(self.message)

class TwoPasswordPromps(Exception):
    "Raised when no device returned second password prompt"
    def __init__(self, host: str, message: str = "Device returned second password prompt") -> None:
        self.serial = host
        self.message = f"{host} - {message}"
        super().__init__(self.message)

class BadDefaultCredentials(Exception):
    "Raised when default credentials weren't usable."
    def __init__(self, host: str, message: str = "Permission denied, default credentials unusable.") -> None:
        self.serial = host
        self.message = f"{host} - {message}"
        super().__init__(self.message)
