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
from typing import Any, Dict, List, Optional, Union

import pydantic
from pydantic import ValidationError
from werkzeug.exceptions import Conflict, NotFound  # type: ignore

from nfv_test_api.host import Host
from nfv_test_api.v2.data.common import CommandStatus
from nfv_test_api.v2.data.namespace import Namespace, NamespaceCreate, NamespaceUpdate
from nfv_test_api.v2.services.base_service import BaseService, K

LOGGER = logging.getLogger(__name__)


class NamespaceService(BaseService[Namespace, NamespaceCreate, NamespaceUpdate]):
    def __init__(self, host: Host) -> None:
        super().__init__(host)

    def get_all_raw(self) -> List[Dict[str, Any]]:
        stdout, stderr = self.host.exec(["ip", "-j", "-details", "netns", "list-id"])
        if stderr:
            raise RuntimeError(f"Failed to run netns list-id command on host: {stderr}")

        raw_namespaces = json.loads(stdout or "[]")
        return pydantic.parse_obj_as(List[Dict[str, Any]], raw_namespaces)

    def get_all(self) -> List[Namespace]:
        namespaces = []
        for raw_namespace in self.get_all_raw():
            try:
                namespace = Namespace(**raw_namespace)
                namespace.attach_host(self.host)
                namespaces.append(namespace)
            except ValidationError as e:
                LOGGER.error(
                    f"Failed to parse a namespace: {raw_namespace}\n" f"{str(e)}"
                )

        return namespaces

    def get_one_raw(self, identifier: str) -> Optional[Dict[str, Any]]:
        raw_namespaces_list = [
            raw_namespace
            for raw_namespace in self.get_all_raw()
            if raw_namespace.get("name", "") == identifier
        ]
        if not raw_namespaces_list:
            return None

        if len(raw_namespaces_list) > 1:
            LOGGER.error(
                f"Expected to get one namespace here but got multiple ones: {raw_namespaces_list}"
            )

        return raw_namespaces_list[0]

    def get_one_or_default(
        self, identifier: str, default: Optional[K] = None
    ) -> Union[Namespace, None, K]:
        raw_namespace = self.get_one_raw(identifier)
        if raw_namespace is None:
            return default

        namespace = Namespace(**raw_namespace)
        namespace.attach_host(self.host)
        return namespace

    def get_one(self, identifier: str) -> Namespace:
        namespace = self.get_one_or_default(identifier)
        if not namespace:
            raise NotFound(f"Could not find any namespace with name {identifier}")

        return namespace

    def create(self, o: NamespaceCreate) -> Namespace:
        existing_namespace = self.get_one_or_default(o.name)
        if existing_namespace:
            raise Conflict("A namespace with this name already exists")

        if o.ns_id is not None:
            if o.ns_id in [ns.ns_id for ns in self.get_all()]:
                raise Conflict("A namespace with this id already exists")

        _, stderr = self.host.exec(["ip", "netns", "add", o.name])
        if stderr:
            raise RuntimeError(f"Failed to create namespace: {stderr}")

        _, stderr = self.host.exec(
            ["ip", "netns", "set", o.name, str(o.ns_id or "auto")]
        )
        if stderr:
            raise RuntimeError(f"Failed to set namespace id: {stderr}")

        existing_namespace = self.get_one_or_default(o.name)
        if existing_namespace:
            return existing_namespace

        raise RuntimeError(
            "The namespace should have been created but can not be found"
        )

    def update(self, identifier: str, o: NamespaceUpdate) -> Namespace:
        raise NotImplementedError("Updating namespaces is not supported")

    def delete(self, identifier: str) -> None:
        existing_namespace = self.get_one_or_default(identifier)
        if not existing_namespace:
            return

        _, stderr = self.host.exec(["ip", "netns", "del", identifier])
        if stderr:
            raise RuntimeError(f"Failed to delete namespace: {stderr}")

        existing_namespace = self.get_one_or_default(identifier)
        if not existing_namespace:
            return

        raise RuntimeError(
            "The namespace should have been deleted but can still be found"
        )

    def status(self) -> CommandStatus:
        command = ["ip", "-details", "netns", "list-id"]
        stdout, stderr = self.host.exec(command)

        return CommandStatus(
            command=command,
            stdout=stdout,
            stderr=stderr,
        )
