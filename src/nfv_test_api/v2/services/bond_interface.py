import logging
from typing import List

from werkzeug.exceptions import BadRequest

from nfv_test_api.host import Host
from nfv_test_api.v2.data import Interface, InterfaceState, InterfaceUpdate, LinkInfo
from nfv_test_api.v2.data.interface import InterfaceCreate

from .interface import InterfaceService

LOGGER = logging.getLogger(__name__)


class BondInterfaceService(InterfaceService):
    def __init__(self, host: Host) -> None:
        super().__init__(host)

    def create(self, o: InterfaceCreate) -> Interface:
        if o.type != LinkInfo.Kind.BOND:
            raise BadRequest(f"You can only create a bond interface with a type bond, got {o.type.name} instead")

        if o.slave_interfaces is None:
            raise BadRequest("You need to specify the slave interfaces for the bond interface you create")

        slave_interfaces = [self.get(identifier) for identifier in o.slave_interfaces]

        interface = super().create(o)
        interface = super().set_state(interface, InterfaceState.DOWN)
        for slave_interface in slave_interfaces:
            slave_interface = super().set_state(slave_interface, InterfaceState.DOWN)
            slave_interface = super().set_master(slave_interface, "nomaster")

        _, stderr = self.host.exec(["sh", "-c", f"echo 4 > /sys/class/net/{interface.if_name}/bonding/mode"])
        if stderr:
            raise RuntimeError(f"Failed to change bonding mode of interface: {stderr}")

        for slave_interface in slave_interfaces:
            slave_interface = super().set_master(slave_interface, "nomaster")
            slave_interface = super().set_state(slave_interface, InterfaceState.UP)

        return super().set_state(interface, InterfaceState.UP)
