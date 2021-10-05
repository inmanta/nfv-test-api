import json
import logging
from ipaddress import IPv4Interface, IPv6Interface, ip_interface
from typing import List, Set, Union

from pydantic import ValidationError
from werkzeug.exceptions import BadRequest, Conflict, NotFound

from nfv_test_api.services.base_service import BaseService, K
from nfv_test_api.data import CommandStatus, Interface
from nfv_test_api.host import Host

LOGGER = logging.getLogger(__name__)


class InterfaceService(BaseService[Interface]):
    def __init__(self, host: Host) -> None:
        super().__init__(host)

    def get_all_raw(self) -> List[object]:
        stdout, stderr = self.host.exec(["ip", "-j", "-details", "addr"])
        if stderr:
            raise RuntimeError(f"Failed to run addr command on host: {stderr}")

        raw_interfaces = json.loads(stdout or "[]")
        if not isinstance(raw_interfaces, list):
            raise RuntimeError(
                f"Failed to parse the list of interfaces.  Expected a list but got a {type(raw_interfaces)}: "
                f"{raw_interfaces}"
            )

        return raw_interfaces

    def get_all(self) -> List[Interface]:
        interfaces: List[Interface] = []
        for raw_interface in self.get_all_raw():
            try:
                interfaces.append(Interface(**raw_interface))
            except ValidationError as e:
                LOGGER.error(f"Failed to parse an interface: {raw_interface}\n" f"{str(e)}")

        return interfaces

    def get_or_default(self, identifier: str, default: K = None) -> Union[Interface, K]:
        for interface in self.get_all():
            if interface.if_name == identifier:
                return interface

        return default

    def get(self, identifier: str) -> Interface:
        interface = self.get_or_default(identifier)
        if not interface:
            raise NotFound(f"Could not find any interface with name {identifier}")

        return interface

    def create(self, o: Interface.CreateForm) -> Interface:
        existing_interface = self.get_or_default(o.name)
        if existing_interface:
            raise Conflict("An interface with this name already exists")

        command = [
            "ip",
            "link",
            "add",
            "name",
            o.name,
        ]
        if o.parent_dev is not None:
            command += ["link", o.parent_dev]

        if o.address is not None:
            command += ["address", o.address]

        if o.broadcast is not None:
            command += ["broadcast", o.broadcast]

        if o.mtu is not None:
            command += ["mtu", o.mtu]

        command += ["type", o.type]
        _, stderr = self.host.exec(command)
        if stderr:
            raise BadRequest(stderr)

        existing_interface = self.get_or_default(o.name)
        if not existing_interface:
            raise RuntimeError("The interface should have been created but can not be found")

        return existing_interface

    def update(self, identifier: str, o: Interface.UpdateForm) -> Interface:
        existing_interface = self.get(identifier)
        existing_addresses: Set[Union[IPv4Interface, IPv6Interface]] = {
            ip_interface(f"{str(addr_info.local)}/{addr_info.prefix_len}") for addr_info in existing_interface.addr_info
        }
        desired_addresses: Set[Union[IPv4Interface, IPv6Interface]] = {interface for interface in o.addresses}

        command = [
            "ip",
            "link",
            "set",
            identifier,
            o.state,
            "mtu",
            o.mtu,
        ]
        if o.master is None:
            command += ["nomaster"]
        else:
            command += ["master", o.master]

        _, stderr = self.host.exec(command)
        if stderr:
            raise BadRequest(stderr)

        extra_addresses = existing_addresses - desired_addresses
        missing_addresses = desired_addresses - existing_addresses

        # Removing additional addresses
        for interface in extra_addresses:
            command = ["ip", "address", "del", str(interface), "dev", identifier]
            _, stderr = self.host.exec(command)
            if stderr:
                raise BadRequest(stderr)

        # Adding missing addresses
        for interface in missing_addresses:
            command = ["ip", "address", "add", str(interface), "dev", identifier]
            _, stderr = self.host.exec(command)
            if stderr:
                raise BadRequest(stderr)

        return self.get(identifier)

    def delete(self, identifier: str) -> None:
        existing_interface = self.get_or_default(identifier)
        if not existing_interface:
            return

        command = ["ip", "link", "del", identifier]
        _, stderr = self.host.exec(command)
        if stderr:
            raise BadRequest(stderr)

    def status(self) -> str:
        command = ["ip", "-details", "addr"]
        stdout, stderr = self.host.exec(command)

        return CommandStatus(command=command, stdout=stdout, stderr=stderr,)
