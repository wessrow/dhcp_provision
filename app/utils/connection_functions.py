#!/usr/bin/python3

"""
Device Connection Logic.
"""

import os
import re
import sys
import logging
import time
import ipaddress
import socket
from contextlib import closing
from subprocess import check_output, CalledProcessError
from jinja2 import Template
from ntc_templates.parse import parse_output
from textfsm import TextFSMError
from scrapli import Scrapli
from scrapli.driver import GenericDriver
from scrapli.exceptions import ScrapliConnectionError, ScrapliAuthenticationFailed, \
                                ScrapliTimeout, ScrapliConnectionNotOpened
from .netbox_functions import NetboxConnector
from .os_download_functions import SFTPConnector
from .exceptions import DeviceNotFound, TwoPasswordPromps, BadDefaultCredentials, UnsupportedOS
from .device_detection_functions import DeviceDetection

# pylint: disable=line-too-long

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout,
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )

# Turns of Scrapli-logging.
logging.getLogger('scrapli').propagate = False

try:
    TFTP_SERVER = os.environ["TFTP_SERVER"]
    NB_API_TOKEN = os.environ["NB_API_TOKEN"]
    # SFTP_SERVER = os.environ["SFTP_SERVER"]
    # SFTP_USER = os.environ["SFTP_USER"]
    # SFTP_PASSWORD = os.environ["SFTP_PASSWORD"]
    # FGT_USER = os.environ["FGT_USER"]
    # FGT_PASS = os.environ["FGT_PASS"]
except KeyError as error:
    logger.error("var %s was not found in the environment. Fatal Error.", error)
    sys.exit(1)

try:
    NETBOX = os.environ["NETBOX_HOST"]
except KeyError:
    logger.warning("$NETBOX_HOST was not set. Using default 'netbox:8080' as host")
    NETBOX = "netbox:8080"

MY_DEVICE = {
    # "auth_username": os.environ["username"],
    # "auth_password": os.environ["password"],
    "auth_username": "admin",
    "auth_password": "",
    "auth_strict_key": False
}

def icmp_test(ip_address: str) -> bool:
    """
    Verifies if IP Address responds to ICMP
    """

    try:
        check_output(["ping", "-c", "3", ip_address])
        return True
    except CalledProcessError:
        return False

def ssh_test(ip_address: str) -> bool:
    """
    Verifies if IP Address accepts TCP/22
    """

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(5)
        test_ssh = sock.connect_ex((ip_address, 22))
        if test_ssh != 0:
            test_status = False
        elif test_ssh == 0:
            test_status = True

    return test_status

def manual_connect_on_open(cls):
    """
    Function to interact with device when normal authentication doesn't work.
    If a device (ArubaCX for example) asks for a new password on login, this is run.
    """
    time.sleep(5)
    cls.channel.write(cls.auth_username)
    cls.channel.send_return()
    time.sleep(10)
    cls.channel.write(cls.auth_password)
    cls.channel.send_return()
    time.sleep(10)
    cls.channel.write(cls.auth_password)
    cls.channel.send_return()

class DeviceConnector:
    """
    SSH Device Connection-functions.
    """

    def __init__(self, host: str, device_type: str, user: str = None, password: str = None) -> None:
        """
        Constructor for the class. Connection is made available.
        """
        self.host = host

        if user is None and password is None:
            self.user = MY_DEVICE["auth_username"]
            self.password = MY_DEVICE["auth_password"]

        try:
            if device_type == "FGT":
                self.device = self._create_forti_object()
            else:
                self.device = self._create_device_object()
            self._open_connection(self.device)

        # If auth fails, verify that the device does not just want 'Enter new password:' prompt.
        except TwoPasswordPromps as logon_error:
            logger.error(logon_error)
            self.device_on_open = self._create_device_object(on_open=manual_connect_on_open, auth_bypass=True)
            self._open_connection(self.device_on_open)

        try:
            self.device_os = self._detect_os()
        except UnsupportedOS as exc:
            raise UnsupportedOS(host=self.host) from exc

        try:
            self.serial = self.get_device_sn()[0]["serial"]
        except TextFSMError as exc:
            raise ScrapliConnectionError from exc

    def _create_device_object(self, on_open = None, auth_bypass: bool = False) -> object:
        """
        """

        return Scrapli(host=self.host,
                        auth_username=self.user,
                        auth_password=self.password,
                        auth_strict_key=MY_DEVICE["auth_strict_key"],
                        timeout_transport=0,
                        timeout_ops=60,
                        platform = "aruba_aoscx",
                        on_open=on_open,
                        auth_bypass=auth_bypass
        )

    def _create_forti_object(self) -> object:
        """
        """

        return GenericDriver(host=self.host,
                        auth_username=self.user,
                        auth_password=self.password,
                        auth_strict_key=MY_DEVICE["auth_strict_key"],
                        timeout_transport=0,
                        timeout_ops=10,
                        comms_prompt_pattern=r"^[a-zA-Z0-9.\-@():]{1,48}\s?[#>$]\s*$"
        )

    def _open_connection(self, connection, max_retries=20, backoff_delay=20):
        """
        Recursive function to help establish connection if device is not responsive
        right away.
        """

        try:
            return connection.open()
        except ScrapliConnectionError as e:
            if max_retries > 0:
                time.sleep(backoff_delay)
                logger.info("%s - Retrying %s more time(s)...", connection.host, max_retries)
                logger.debug(e)
                return self._open_connection(connection, max_retries - 1, backoff_delay)
            logger.error("Max retries reached. Giving up.")
            return None
        except ScrapliAuthenticationFailed as auth_error:
            if str(auth_error) == "password prompt seen more than once, assuming auth failed":
                raise TwoPasswordPromps(str(self.host)) from auth_error

            raise BadDefaultCredentials(str(self.host)) from auth_error

    def _detect_os(self):
        """
        """

        detect_os = DeviceDetection(conn=self.device)
        return detect_os.get_device_os()

    @staticmethod
    def _parse_tftp_output(output: str, success: str="Copying configuration: [Success]") -> bool:
        """
        Parses output of copy tftp-command.
        """

        if success in output:
            return True
        return False

    def reload_device(self):
        """
        Reloads device.
        """

        logger.info("%s - Device will reload..", self.serial)

        try:
            self.device.send_interactive(self.device_os["reload_command"])
        except ScrapliTimeout:
            logger.info("%s - Device reloaded!", self.serial)

    def get_device_sn(self) -> str:
        """
        Parse device SN from device.
        """

        result = self.device.send_command(self.device_os["system_command"]).result

        return parse_output(platform=self.device_os["os_slug"], command=self.device_os["system_command"], data=result)

    def get_device_version(self) -> str:
        """
        Gets device OS version.
        """

        result = self.device.send_command(self.device_os["images_command"]).result

        verify_os = re.search(self.device_os["verify_os_regex"], result)
        if verify_os:
            logger.info("%s - Verifying OS - %s", self.serial, verify_os.group(1))
            time.sleep(30)
            return self.get_device_version()

        return re.search(self.device_os["os_regex"], result).group(1)

    def download_os_primary(self, os_image: str) -> None:
        """
        Downloads OS as primary device OS.
        """

        logger.info("%s - New OS '%s' will be downloaded.", self.serial, os_image)

        # FIXME Not dynamic
        self.device.send_interactive([
            (f"copy sftp://{SFTP_USER}@{SFTP_SERVER}/{os_image} primary", "Continue (y/n)? "),
            ("y", "Are you sure you want to continue connecting (yes/no/[fingerprint])? "),
            ("yes", f"{SFTP_USER}@{SFTP_SERVER}'s password: "),
            (SFTP_PASSWORD, "", True)
        ], timeout_ops=1200)

        logger.info("%s - New OS downloaded successfully.", self.serial)

    def get_interfaces_number(self) -> list:
        """
        Returns list of all physical interfaces available on the device.
        """

        result = self.device.send_command(self.device_os["interfaces_command"]).result

        return parse_output(platform=self.device_os["os_slug"], command=self.device_os["interfaces_command"], data=result)

    def copy_config(self, serial: str, data_store: str, device_ip: str=None):
        """
        Copy created config to device via TFTP.
        """

        if device_ip is None:
            device_ip = self.host

        result = None
        logger.info("%s - Device will have its %s loaded (connected via %s, device configured IP will be %s)", self.serial, data_store, self.host, device_ip)

        try:
            result = self.device.send_command(self.device_os['copy_config_command'].format(tftp_server=TFTP_SERVER,
                                                                                            serial=self.serial,
                                                                                            data_store=data_store),
                                            timeout_ops=300).result
        except ScrapliTimeout:
            ssh_test_result = ssh_test(device_ip)
            icmp_test_result = icmp_test(device_ip)
            if ssh_test_result is True and icmp_test_result is True:
                logger.info("%s - Configuration for device successfully updated", serial)
            else:
                logger.info("%s - SSH Test: %s - ICMP Test: %s", serial, ssh_test_result, icmp_test_result)
                logger.error("%s - Configuration for device failed", serial)
        if result is not None:
            if self._parse_tftp_output(result):
                logger.info("%s - Configuration for device successfully updated", serial)
            else:
                logger.error("%s - Configuration for device failed: %s", serial, result)

    def generate_api_key(self, admin_user: str):
        """
        Generates API Key for Fortigate Firewall.
        """

        try:
            result = self.device.send_command(f"execute api-user generate-key {admin_user}")
        except ScrapliTimeout:
            logger.error("%s - Configuration for device failed", self.host)

        return result

def render_template(template: str, data: dict):
    """
    Render template with passed data.
    """

    with open(f"./app/utils/templates/{template}", "r", encoding="utf-8") as temp:
        template = Template(temp.read())

    config = template.render(hostname=data["hostname"],
                             ip_address=data["ip_address"],
                             default_gw=data["default_gw"],
                             fallback_vlan=data["fallback_vlan"],
                             interfaces=data["interfaces"],
                             radius_servers=data["radius_servers"]
                            )

    return config

def os_handler(conn, netbox, serial: str):
    """
    Handling of OS verification and upgrade.
    """

    product_raw = conn.get_device_sn()[0]["product"]
    product = re.search(r"([\w]*)\s", product_raw).group(1)

    logger.info("Device Model indentified as: %s", product)

    # sftp = SFTPConnector(SFTP_SERVER, SFTP_USER, SFTP_PASSWORD)

    device_os = conn.get_device_version()

    logger.info("Device OS-version (SHA256 HASH) indentified as: %s", device_os)

    try:
        desired_os = "468450af91ffd58ccafc700e72767a6be81fcbc1ce9fb43c1c74f700272c937f"
    except KeyError:
        logger.error("Unsupported model - verify OS_info for supported models.")
        netbox.update_device_status(serial=serial, status="failed")
        return True

    tags = netbox.get_device_tags(serial)

    for tag in tags:
        if str(tag) == "Upgrading":
            logger.info("%s - Device is still upgrading.", serial)
            return True

    if not bool(device_os == desired_os):
        logger.warning("%s - OS Does NOT match", serial)
        netbox.update_device_tag(serial=serial, tags=[{"slug": "upgrading"}])
        conn.download_os_primary(desired_os["image"])
        conn.get_device_version()
        netbox.update_device_tag(serial=serial, tags=[{"slug": "reloading"}])
        conn.reload_device()
        return True
    logger.info("Device OS matches golden image hash - no upgrade required.")
    return False

def device_already_active(serial, ip_address):
    """
    Verifies whether device IP is already in use or not.
    """

    no_cidr_ip = ip_address.split("/", maxsplit=1)[0]
    if ssh_test(no_cidr_ip) and icmp_test(no_cidr_ip) is not False:
        logger.error("%s - Device IP %s is already active.", serial, no_cidr_ip)
        return True
    return False

def local_radius_server(netbox, serial):
    """
    Sets radius to the local one for the country.
    """

    country = netbox.get_site_name(serial)

    se_radius = "10.39.0.13"
    no_radius = "10.102.200.10"
    fi_radius = "10.241.200.10"
    dk_radius = "10.45.2.10"

    if "SE" in country:
        radius_servers = [se_radius, no_radius, dk_radius, fi_radius]
    if "NO" in country:
        radius_servers = [no_radius, se_radius, dk_radius, fi_radius]
    if "FI" in country:
        radius_servers = [fi_radius, se_radius, dk_radius, no_radius]
    if "DK" in country:
        radius_servers = [dk_radius, se_radius, no_radius, fi_radius]

    return radius_servers

# def api_main(device):
#     """
#     """

#     nb = NetboxConnector("netbox:8080", NB_API_TOKEN)
#     ip_address = nb.get_primary_ip(serial=None, hostname=device["hostname"])
#     no_cidr_ip = ip_address.split("/", maxsplit=1)[0]

#     conn = DeviceConnector(host=no_cidr_ip, device_type="FGT", user=FGT_USER, password=FGT_PASS)

#     logger.info(conn.generate_api_key("faultfinder_api"))

def main(device):
    """
    Ties it all together.
    """

    try:
        try:
            conn = DeviceConnector(host=device["ip"], device_type="Aruba")
        except (BadDefaultCredentials, ScrapliConnectionError, UnsupportedOS) as exc:
            logger.error(exc)
            return None

        nb = NetboxConnector(NETBOX, NB_API_TOKEN)

        serial = conn.get_device_sn()[0]["serial"]

        logger.info("Device Serial indentified as: %s", serial)

        try:
            nb.update_device_status(serial=serial, status="staged")
            hostname = nb.get_device_name(serial)
            ip_address = nb.get_primary_ip(serial)
            device_role = nb.get_device_role(serial)

        except DeviceNotFound as device_error:
            logger.error(device_error)
            return None
        
        logger.info("NetBox examined for device '%s' - found got following data:\nHostname: %s\nIP Address: %s\nDevice Role: %s", serial, hostname, ip_address, device_role)

        if os_handler(conn=conn, netbox=nb, serial=serial) is True:
            return None

        interfaces = conn.get_interfaces_number()

        if device_already_active(serial, ip_address) is True:
            return None

        fallback_vlan = "30"
        if device_role == "Access-Industry":
            fallback_vlan = "54"

        hostname = nb.get_device_name(serial)
        radius_servers = local_radius_server(netbox=nb, serial=serial)

        with open(f"/tftpboot/{serial}.conf", "w", encoding="utf-8") as file:

            data = {"hostname": hostname,
                    "ip_address": ip_address,
                    "default_gw": ipaddress.ip_network(ip_address, strict=False)[1],
                    "fallback_vlan": fallback_vlan,
                    "interfaces": interfaces,
                    "radius_servers": radius_servers}

            logger.info("%s - Created file %s.conf", serial, serial)
            file.write(render_template(template=f"{conn.device_os['os_slug']}.j2", data=data))

        nb.update_device_tag(serial=serial, tags=[{"slug": "configuring"}])
        no_cidr_ip = ip_address.split("/", maxsplit=1)[0]
        conn.copy_config(serial=serial, device_ip=no_cidr_ip, data_store="startup-config")
        # conn.copy_config(serial=serial, device_ip=no_cidr_ip, data_store="running-config")
        # nb.update_device_tag(serial=serial, tags=[])
        return True

    except (ScrapliConnectionNotOpened, ScrapliTimeout):
        logger.error("%s - %s Connection to device was terminated before completion.", serial, device["ip"])
        try:
            nb.update_device_status(serial=serial, status="failed")
            nb.update_device_tag(serial=serial, tags=[])
        except UnboundLocalError:
            logger.info("Device serial unknown, no Netbox update.")
        return False

if __name__ == "__main__":

    pass
    # nb = NetboxConnector("localhost:8000", NB_API_TOKEN)
    # print(nb.get_device_role("CN33L3NJWL"))
