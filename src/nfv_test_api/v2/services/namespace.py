import json
import logging
from typing import List, Union

from pydantic import ValidationError
from werkzeug.exceptions import NotFound

from nfv_test_api.host import Host
from nfv_test_api.v2.data import CommandStatus, Namespace, NamespaceCreate, NamespaceUpdate

from .base_service import BaseService, K

LOGGER = logging.getLogger(__name__)


class NamespaceService(BaseService[Namespace]):
    def __init__(self, host: Host) -> None:
        super().__init__(host)

    def get_all_raw(self) -> List[object]:
        stdout, stderr = self.host.exec(["ip", "-j", "-details", "netns", "list-id"])
        if stderr:
            raise RuntimeError(f"Failed to run netns list-id command on host: {stderr}")

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
                namespace = Namespace(**raw_namespace)
                namespace.attach_host(self.host)
                namespaces.append(namespace)
            except ValidationError as e:
                LOGGER.error(f"Failed to parse a namespace: {raw_namespace}\n" f"{str(e)}")

        return namespaces

    def get_or_default(self, identifier: str, default: K = None) -> Union[Namespace, K]:
        for namespace in self.get_all():
            if namespace.name == identifier:
                return namespace

        return default

    def get(self, identifier: str) -> Namespace:
        namespace = self.get_or_default(identifier)
        if not namespace:
            raise NotFound(f"Could not find any namespace with name {identifier}")

        return namespace

    def create(self, o: NamespaceCreate) -> Namespace:
        existing_namespace = self.get_or_default(o.name)
        if existing_namespace:
            return existing_namespace

        _, stderr = self.host.exec(["ip", "netns", "add", o.name])
        if stderr:
            raise RuntimeError(f"Failed to create namespace: {stderr}")

        _, stderr = self.host.exec(["ip", "netns", "set", o.name, "auto"])
        if stderr:
            raise RuntimeError(f"Failed to set namespace id: {stderr}")

        existing_namespace = self.get_or_default(o.name)
        if existing_namespace:
            return existing_namespace

        raise RuntimeError("The namespace should have been created but can not be found")

    def update(self, identifier: str, o: NamespaceUpdate) -> Namespace:
        raise NotImplementedError("Updating namespaces is not supported")

    def delete(self, identifier: str) -> None:
        existing_namespace = self.get_or_default(identifier)
        if not existing_namespace:
            return

        _, stderr = self.host.exec(["ip", "netns", "del", identifier])
        if stderr:
            raise RuntimeError(f"Failed to delete namespace: {stderr}")

        existing_namespace = self.get_or_default(identifier)
        if not existing_namespace:
            return

        raise RuntimeError("The namespace should have been deleted but can still be found")

    def status(self) -> str:
        command = ["ip", "-details", "netns", "list-id"]
        stdout, stderr = self.host.exec(command)

        return CommandStatus(command=command, stdout=stdout, stderr=stderr,)
