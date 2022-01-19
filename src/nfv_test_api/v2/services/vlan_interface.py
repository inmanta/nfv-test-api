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

from werkzeug.exceptions import BadRequest, Conflict  # type: ignore

from nfv_test_api.host import Host
from nfv_test_api.v2.data.interface import Interface, InterfaceCreate, LinkInfo
from nfv_test_api.v2.services.interface import InterfaceService

LOGGER = logging.getLogger(__name__)


class VlanInterfaceService(InterfaceService):
    def __init__(self, host: Host) -> None:
        super().__init__(host)

    def create(self, o: InterfaceCreate) -> Interface:
        if o.type != LinkInfo.Kind.VLAN:
            raise BadRequest(f"You can only create a vlan interface with a type vlan, got {o.type.name} instead")

        if o.parent_dev is None:
            raise BadRequest("You need to specify the parent interface for the vlan interface you create")

        existing_interface = self.get_one_or_default(o.name)
        if existing_interface:
            raise Conflict("An interface with this name already exists")

        # Ensuring parent interface exists
        self.get_one(o.parent_dev)
        try:
            if not o.name.startswith(o.parent_dev):
                raise ValueError(f"'{o.name}' doesn't start with '{o.parent_dev}'")

            vlan_id = int(o.name.split(".")[-1])
        except ValueError as e:
            LOGGER.error(str(e))
            raise BadRequest("A vlan type interface should be named with the following format: <parent_dev>.<vlan_id>")

        command = [
            "ip",
            "link",
            "add",
            "name",
            o.name,
            "link",
            o.parent_dev,
        ]

        if o.address is not None:
            command += ["address", str(o.address)]

        if o.broadcast is not None:
            command += ["broadcast", str(o.broadcast)]

        if o.mtu is not None:
            command += ["mtu", str(o.mtu)]

        command += ["type", "vlan", "id", str(vlan_id)]
        _, stderr = self.host.exec(command)
        if stderr:
            raise RuntimeError(f"Failed to create interface with command {command}: {stderr}")

        existing_interface = self.get_one_or_default(o.name)
        if not existing_interface:
            raise RuntimeError("The interface should have been created but can not be found")

        return existing_interface
