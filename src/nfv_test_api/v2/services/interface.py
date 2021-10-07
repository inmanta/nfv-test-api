import json
import logging
from ipaddress import IPv4Interface, IPv6Interface, ip_interface
from typing import List, Set, Union

from pydantic import ValidationError
from werkzeug.exceptions import Conflict, NotFound

from nfv_test_api.host import Host, NamespaceHost
from nfv_test_api.v2.data import CommandStatus, Interface, InterfaceCreate, InterfaceUpdate
from nfv_test_api.v2.data.interface import InterfaceState

from .base_service import BaseService, K

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
                interface = Interface(**raw_interface)
                interface.attach_host(self.host)
                interfaces.append(interface)
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

    def create(self, o: InterfaceCreate) -> Interface:
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
            raise RuntimeError(f"Failed to create interface with command {command}: {stderr}")

        existing_interface = self.get_or_default(o.name)
        if not existing_interface:
            raise RuntimeError("The interface should have been created but can not be found")

        return existing_interface

    def update(self, identifier: str, o: InterfaceUpdate) -> Interface:
        interface = self.get(identifier)

        if o.mtu is not None:
            interface = self.set_mtu(interface, o.mtu)

        if o.master is not None:
            interface = self.set_master(interface, o.master)

        if o.state is not None:
            interface = self.set_state(interface, o.state)

        if o.addresses is not None:
            existing_addresses: Set[Union[IPv4Interface, IPv6Interface]] = {
                ip_interface(f"{str(addr_info.local)}/{addr_info.prefix_len}") for addr_info in interface.addr_info
            }
            desired_addresses: Set[Union[IPv4Interface, IPv6Interface]] = {addr for addr in o.addresses}

            extra_addresses = existing_addresses - desired_addresses
            missing_addresses = desired_addresses - existing_addresses

            for addr in extra_addresses:
                interface = self.del_address(interface, addr)

            for addr in missing_addresses:
                interface = self.add_address(interface, addr)

        if o.name is not None:
            interface = self.rename(interface, o.name)

        if o.netns is not None:
            # This should be called last,
            interface = self.move(interface, o.netns)

        return interface

    def set_state(self, interface: Interface, state: InterfaceState) -> Interface:
        command = [
            "ip",
            "link",
            "set",
            interface.if_name,
            state.name.lower(),
        ]
        _, stderr = interface.host.exec(command)
        if stderr:
            raise RuntimeError(f"Failed to set link state with command {command}: {stderr}")

        return self.get(interface.if_name)

    def set_mtu(self, interface: Interface, mtu: int) -> Interface:
        command = [
            "ip",
            "link",
            "set",
            interface.if_name,
            "mtu",
            str(mtu),
        ]
        _, stderr = interface.host.exec(command)
        if stderr:
            raise RuntimeError(f"Failed to set link mtu with command {command}: {stderr}")

        return self.get(interface.if_name)

    def set_master(self, interface: Interface, new_master: str) -> Interface:
        command = [
            "ip",
            "link",
            "set",
            "dev",
            interface.if_name,
        ]

        if new_master == "nomaster":
            command += ["nomaster"]
        else:
            command += ["master", new_master]

        _, stderr = interface.host.exec(command)
        if stderr:
            raise RuntimeError(f"Failed to set link master with command {command}: {stderr}")

        return self.get(interface.if_name)

    def add_address(self, interface: Interface, address: Union[IPv4Interface, IPv6Interface]) -> Interface:
        command = [
            "ip",
            "address",
            "add",
            str(address),
            "dev",
            interface.if_name,
        ]
        _, stderr = interface.host.exec(command)
        if stderr:
            raise RuntimeError(f"Failed to add address with command {command}: {stderr}")

        return self.get(interface.if_name)

    def del_address(self, interface: Interface, address: Union[IPv4Interface, IPv6Interface]) -> Interface:
        command = [
            "ip",
            "address",
            "del",
            str(address),
            "dev",
            interface.if_name,
        ]
        _, stderr = interface.host.exec(command)
        if stderr:
            raise RuntimeError(f"Failed to delete address with command {command}: {stderr}")

        return self.get(interface.if_name)

    def rename(self, interface: Interface, new_name: str) -> Interface:
        command = [
            "ip",
            "link",
            "set",
            "dev",
            interface.if_name,
            "name",
            new_name,
        ]
        _, stderr = interface.host.exec(command)
        if stderr:
            raise RuntimeError(f"Failed to rename interface with command {command}: {stderr}")

        return self.get(new_name)

    def move(self, interface: Interface, new_namespace: str) -> Interface:
        command = [
            "ip",
            "link",
            "set",
            "dev",
            interface.if_name,
            "netns",
            new_namespace,
        ]
        _, stderr = interface.host.exec(command)
        if stderr:
            raise RuntimeError(f"Failed to move interface to new namespace with command {command}: {stderr}")

        return InterfaceService(NamespaceHost(new_namespace)).get(interface.if_name)

    def delete(self, identifier: str) -> None:
        existing_interface = self.get_or_default(identifier)
        if not existing_interface:
            return

        command = ["ip", "link", "del", identifier]
        _, stderr = existing_interface.host.exec(command)
        if stderr:
            raise RuntimeError(f"Failed to delete interface with command {command}: {stderr}")

    def status(self) -> str:
        command = ["ip", "-details", "addr"]
        stdout, stderr = self.host.exec(command)

        return CommandStatus(command=command, stdout=stdout, stderr=stderr,)
