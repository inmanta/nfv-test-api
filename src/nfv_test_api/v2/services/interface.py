"""
       Copyright 2021 Inmanta

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
import json
import logging
from ipaddress import IPv4Interface, IPv6Interface, ip_interface
from typing import Any, Dict, List, Optional, Set, Union

import pydantic
from pydantic import ValidationError
from werkzeug.exceptions import Conflict, NotFound  # type: ignore

from nfv_test_api.host import Host, NamespaceHost
from nfv_test_api.v2.data.common import CommandStatus
from nfv_test_api.v2.data.interface import (
    Interface,
    InterfaceCreate,
    InterfaceState,
    InterfaceUpdate,
)
from nfv_test_api.v2.services.base_service import BaseService, K
from nfv_test_api.v2.services.namespace import NamespaceService

LOGGER = logging.getLogger(__name__)


class InterfaceService(BaseService[Interface, InterfaceCreate, InterfaceUpdate]):
    def __init__(self, host: Host) -> None:
        super().__init__(host)

    def get_all_raw(self) -> List[Dict[str, Any]]:
        stdout, stderr = self.host.exec(["ip", "-j", "-details", "addr"])
        if stderr:
            raise RuntimeError(f"Failed to run addr command on host: {stderr}")

        raw_interfaces = json.loads(stdout or "[]")
        return pydantic.parse_obj_as(List[Dict[str, Any]], raw_interfaces)

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

    def get_one_raw(self, identifier: str) -> Optional[Dict[str, Any]]:
        stdout, stderr = self.host.exec(["ip", "-j", "-details", "addr", "show", identifier])
        if stderr.strip() == f'Device "{identifier}" does not exist.':
            return None

        if stderr:
            raise RuntimeError(f"Failed to get an addr on host: {stderr}")

        raw_interfaces = json.loads(stdout or "[]")
        raw_interfaces_list = pydantic.parse_obj_as(List[Dict[str, Any]], raw_interfaces)
        if not raw_interfaces_list:
            return None

        if len(raw_interfaces_list) > 1:
            LOGGER.error(f"Expected to get one interface here but got multiple ones: {raw_interfaces_list}")

        return raw_interfaces_list[0]

    def get_one_or_default(self, identifier: str, default: Optional[K] = None) -> Union[Interface, None, K]:
        raw_interface = self.get_one_raw(identifier)
        if raw_interface is None:
            return default

        interface = Interface(**raw_interface)
        interface.attach_host(self.host)
        return interface

    def get_one(self, identifier: str) -> Interface:
        interface = self.get_one_or_default(identifier)
        if not interface:
            raise NotFound(f"Could not find any interface with name {identifier}")

        return interface

    def create(self, o: InterfaceCreate) -> Interface:
        existing_interface = self.get_one_or_default(o.name)
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
            command += ["address", str(o.address)]

        if o.broadcast is not None:
            command += ["broadcast", str(o.broadcast)]

        if o.mtu is not None:
            command += ["mtu", str(o.mtu)]

        command += ["type", o.type]
        _, stderr = self.host.exec(command)
        if stderr:
            raise RuntimeError(f"Failed to create interface with command {command}: {stderr}")

        existing_interface = self.get_one_or_default(o.name)
        if not existing_interface:
            raise RuntimeError("The interface should have been created but can not be found")

        return existing_interface

    def update(self, identifier: str, o: InterfaceUpdate) -> Interface:
        interface = self.get_one(identifier)

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

        return self.get_one(interface.if_name)

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

        return self.get_one(interface.if_name)

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

        return self.get_one(interface.if_name)

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

        return self.get_one(interface.if_name)

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

        return self.get_one(interface.if_name)

    def rename(self, interface: Interface, new_name: str) -> Interface:
        previous_state = interface.oper_state
        if previous_state == InterfaceState.UP:
            # The interface needs to be down for renaming it
            interface = self.set_state(interface, InterfaceState.DOWN)

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

        interface = self.get_one(new_name)
        if previous_state == InterfaceState.UP:
            interface = self.set_state(interface, InterfaceState.UP)

        return interface

    def move(self, interface: Interface, new_namespace: Union[str, int]) -> Interface:
        namespace_name: Optional[str] = None
        if isinstance(new_namespace, int):
            for namespace in NamespaceService(self.host).get_all():
                if namespace.ns_id == new_namespace:
                    namespace_name = namespace.name
                    break
        else:
            NamespaceService(Host()).get_one(new_namespace)
            namespace_name = new_namespace

        if not namespace_name:
            raise NotFound(f"Couldn't find any namespace with id {new_namespace}")

        previous_state = interface.oper_state
        if previous_state == InterfaceState.UP:
            # The interface needs to be down for moving it
            interface = self.set_state(interface, InterfaceState.DOWN)

        command = [
            "ip",
            "link",
            "set",
            "dev",
            interface.if_name,
            "netns",
            namespace_name,
        ]
        _, stderr = interface.host.exec(command)
        if stderr:
            raise RuntimeError(f"Failed to move interface to new namespace with command {command}: {stderr}")

        interface = InterfaceService(NamespaceHost(namespace_name)).get_one(interface.if_name)
        if previous_state == InterfaceState.UP:
            interface = self.set_state(interface, InterfaceState.UP)

        return interface

    def delete(self, identifier: str) -> None:
        existing_interface = self.get_one_or_default(identifier)
        if not existing_interface:
            return

        command = ["ip", "link", "del", identifier]
        _, stderr = existing_interface.host.exec(command)
        if stderr:
            raise RuntimeError(f"Failed to delete interface with command {command}: {stderr}")

    def status(self) -> CommandStatus:
        command = ["ip", "-details", "addr"]
        stdout, stderr = self.host.exec(command)

        return CommandStatus(
            command=command,
            stdout=stdout,
            stderr=stderr,
        )
