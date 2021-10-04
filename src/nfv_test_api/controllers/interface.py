from typing import List, Optional
from nfv_test_api.controllers.base_controller import BaseController
from nfv_test_api.data import CommandStatus, Interface
from nfv_test_api.host import Host
from pydantic import ValidationError
import json
import logging


LOGGER = logging.getLogger(__name__)


class InterfaceController(BaseController[Interface]):
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

    def get(self, identifier: str) -> Optional[Interface]:
        for interface in self.get_all():
            if interface.if_name == identifier:
                return interface
            
        return None

    def create(self, o: Interface.CreateForm) -> Interface:
        
        return super().create(o)

    def update(self, identifier: str, o: Interface.UpdateForm) -> Interface:
        return super().update(identifier, o)

    def delete(self, identifier: str) -> None:
        return super().delete(identifier)

    def status(self) -> str:
        command = ["ip", "-details", "addr"]
        stdout, stderr = self.host.exec(command)
        
        return CommandStatus(
            command=command,
            stdout=stdout,
            stderr=stderr,
        )
