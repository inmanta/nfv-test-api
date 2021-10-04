from typing import List, Optional
from nfv_test_api.controllers.base_controller import BaseController
from nfv_test_api.data import CommandStatus, Namespace
from nfv_test_api.host import Host
from pydantic import ValidationError
import json
import logging


LOGGER = logging.getLogger(__name__)


class NamespaceController(BaseController[Namespace]):
    def __init__(self, host: Host) -> None:
        super().__init__(host)

    def get_all_raw(self) -> List[object]:
        stdout, stderr = self.host.exec(["ip", "-j", "-details", "netns", "list"])
        if stderr:
            raise RuntimeError(f"Failed to run netns list command on host: {stderr}")

        raw_namespaces = json.loads(stdout or "[]")
        if not isinstance(raw_namespaces, list):
            raise RuntimeError(
                f"Failed to parse the list of namespaces.  Expected a list but got a {type(raw_namespaces)}: "
                f"{raw_namespaces}"
            )

        return raw_namespaces

    def get_all(self) -> List[Namespace]:
        namespaces = []
        for raw_namespace in self.get_all_raw():
            try:
                namespaces.append(Namespace(**raw_namespace))
            except ValidationError as e:
                LOGGER.error(f"Failed to parse a namespace: {raw_namespace}\n" f"{str(e)}")

        return namespaces

    def get(self, identifier: str) -> Optional[Namespace]:
        for namespace in self.get_all():
            if namespace.name == identifier:
                return namespace

        return None

    def create(self, o: Namespace.CreateForm) -> Namespace:
        existing_namespace = self.get(o.name)
        if existing_namespace:
            return existing_namespace

        _, stderr = self.host.exec(["ip", "netns", "add", o.name])
        if stderr:
            raise RuntimeError(f"Failed to create namespace: {stderr}")

        existing_namespace = self.get(o.name)
        if existing_namespace:
            return existing_namespace

        raise RuntimeError("The namespace should have been created but can not be found")

    def update(self, identifier: str, o: Namespace.UpdateForm) -> Namespace:
        raise NotImplementedError("Updating namespaces is not supported")

    def delete(self, identifier: str) -> None:
        existing_namespace = self.get(identifier)
        if not existing_namespace:
            return

        _, stderr = self.host.exec(["ip", "netns", "del", identifier])
        if stderr:
            raise RuntimeError(f"Failed to delete namespace: {stderr}")

        existing_namespace = self.get(identifier)
        if not existing_namespace:
            return

        raise RuntimeError("The namespace should have been deleted but can still be found")

    def status(self) -> str:
        command = ["ip", "-details", "netns", "list"]
        stdout, stderr = self.host.exec(command)
        
        return CommandStatus(
            command=command,
            stdout=stdout,
            stderr=stderr,
        )
