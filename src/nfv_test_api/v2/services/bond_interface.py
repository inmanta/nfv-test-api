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
import logging

from werkzeug.exceptions import BadRequest  # type: ignore

from nfv_test_api.host import Host
from nfv_test_api.v2.data.interface import (
    Interface,
    InterfaceCreate,
    InterfaceState,
    LinkInfo,
)
from nfv_test_api.v2.services.interface import InterfaceService

LOGGER = logging.getLogger(__name__)


class BondInterfaceService(InterfaceService):
    def __init__(self, host: Host) -> None:
        super().__init__(host)

    def create(self, o: InterfaceCreate) -> Interface:
        if o.type != LinkInfo.Kind.BOND:
            raise BadRequest(f"You can only create a bond interface with a type bond, got {o.type.name} instead")

        if o.slave_interfaces is None:
            raise BadRequest("You need to specify the slave interfaces for the bond interface you create")

        slave_interfaces = [self.get_one(identifier) for identifier in o.slave_interfaces]

        interface = super().create(o)
        interface = self.set_state(interface, InterfaceState.DOWN)
        for slave_interface in slave_interfaces:
            slave_interface = self.set_state(slave_interface, InterfaceState.DOWN)
            slave_interface = self.set_master(slave_interface, "nomaster")

        _, stderr = self.host.exec(["sh", "-c", f"echo 4 > /sys/class/net/{interface.if_name}/bonding/mode"])
        if stderr:
            raise RuntimeError(f"Failed to change bonding mode of interface: {stderr}")

        for slave_interface in slave_interfaces:
            slave_interface = self.set_master(slave_interface, interface.if_name)
            slave_interface = self.set_state(slave_interface, InterfaceState.UP)

        return self.set_state(interface, InterfaceState.UP)
