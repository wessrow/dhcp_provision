#!/usr/bin/python

"""
Class/functions to help interact with Netbox
"""

import pynetbox
from .exceptions import DeviceNotFound

class NetboxConnector:
    """
    Netbox connection helper.
    """

    def __init__(self, host: str, token: str) -> None:
        """
        Constructor - creates connection to run API-calls to.
        """

        self.netbox = pynetbox.api(url=f"http://{host}", token=token)

    def get_primary_ip(self, serial: str, hostname: str = None) -> str:
        """
        Returns device primary IP.
        """

        if hostname is not None:
            try:
                return str(self.netbox.dcim.devices.get(name=hostname).primary_ip)
            except AttributeError as error:
                raise DeviceNotFound(serial=serial) from error

        try:
            return str(self.netbox.dcim.devices.get(serial=serial).primary_ip)
        except AttributeError as error:
            raise DeviceNotFound(serial=serial) from error

    def get_device_role(self, serial: str) -> str:
        """
        Returns device role.
        """

        try:
            return str(self.netbox.dcim.devices.get(serial=serial).device_role)
        except AttributeError as error:
            raise DeviceNotFound(serial=serial) from error

    def get_device_tags(self, serial: str) -> str:
        """
        Returns device role.
        """

        try:
            return self.netbox.dcim.devices.get(serial=serial).tags
        except AttributeError as error:
            raise DeviceNotFound(serial=serial) from error

    def get_device_name(self, serial: str) -> str:
        """
        Returns device (host)name.
        """

        try:
            return str(self.netbox.dcim.devices.get(serial=serial).name)
        except AttributeError as error:
            raise DeviceNotFound(serial=serial) from error

    def get_site_name(self, serial: str) -> str:
        """
        Returns device site name.
        """

        try:
            return str(self.netbox.dcim.devices.get(serial=serial).site.name)
        except AttributeError as error:
            raise DeviceNotFound(serial=serial) from error

    def update_device_status(self, serial: str, status: str) -> str:
        """
        Update device status.
        """

        try:
            device_id = self.netbox.dcim.devices.get(serial=serial).id
        except AttributeError as error:
            raise DeviceNotFound(serial=serial) from error

        return self.netbox.dcim.devices.update([{"id": device_id, "status": status}])

    def update_device_tag(self, serial: str, tags: list) -> str:
        """
        Update device tags.
        """

        try:
            device_id = self.netbox.dcim.devices.get(serial=serial).id
        except AttributeError as error:
            raise DeviceNotFound(serial=serial) from error

        return self.netbox.dcim.devices.update([{"id": device_id, "tags": tags}])

if __name__ == "__main__":

    pass
    # import os
    # NB_API_TOKEN = os.environ["NB_API_TOKEN"]
    # nb = NetboxConnector("localhost:8000", NB_API_TOKEN)
