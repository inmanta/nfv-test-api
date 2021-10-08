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
from werkzeug.exceptions import NotFound  # type: ignore

from nfv_test_api.host import Host
from nfv_test_api.v2.data.common import CommandStatus
from nfv_test_api.v2.data.route import Route, RouteCreate, RouteUpdate
from nfv_test_api.v2.services.base_service import BaseService, K

LOGGER = logging.getLogger(__name__)


class RouteService(BaseService[Route, RouteCreate, RouteUpdate]):
    def __init__(self, host: Host) -> None:
        super().__init__(host)

    def get_all_raw(self) -> List[Dict[str, Any]]:
        stdout, stderr = self.host.exec(["ip", "-j", "-details", "route"])
        if stderr:
            raise RuntimeError(f"Failed to run route command on host: {stderr}")

        raw_routes = json.loads(stdout or "[]")
        return pydantic.parse_obj_as(List[Dict[str, Any]], raw_routes)

    def get_all(self) -> List[Route]:
        routes: List[Route] = []
        for raw_route in self.get_all_raw():
            try:
                route = Route(**raw_route)
                route.attach_host(self.host)
                routes.append(route)
            except ValidationError as e:
                LOGGER.error(f"Failed to parse a route: {raw_route}\n" f"{str(e)}")

        return routes

    def get_one_raw(self, identifier: str) -> Optional[Dict[str, Any]]:
        stdout, stderr = self.host.exec(["ip", "-j", "-details", "route", "show", identifier])
        if stderr:
            raise RuntimeError(f"Failed to get a route on host: {stderr}")

        raw_routes = json.loads(stdout or "[]")
        raw_routes_list = pydantic.parse_obj_as(List[Dict[str, Any]], raw_routes)
        if not raw_routes_list:
            return None

        if len(raw_routes_list) > 1:
            LOGGER.error(f"Expected to get one interface here but got multiple ones: {raw_routes_list}")

        return raw_routes_list[0]

    def get_one_or_default(self, identifier: str, default: Optional[K] = None) -> Union[Route, None, K]:
        raw_route = self.get_one_raw(identifier)
        if raw_route is None:
            return default

        route = Route(**raw_route)
        route.attach_host(self.host)
        return route

    def get_one(self, identifier: str) -> Route:
        route = self.get_one_or_default(identifier)
        if not route:
            raise NotFound(f"Could not find any route with destination {identifier}")

        return route

    def create(self, o: RouteCreate) -> Route:
        raise NotImplementedError("Creation of route is not supported yet")

    def update(self, identifier: str, o: RouteUpdate) -> Route:
        raise NotImplementedError("Updating of route is not supported yet")

    def delete(self, identifier: str) -> None:
        raise NotImplementedError("Deleting of route is not supported yet")

    def status(self) -> CommandStatus:
        command = ["ip", "-details", "route"]
        stdout, stderr = self.host.exec(command)

        return CommandStatus(
            command=command,
            stdout=stdout,
            stderr=stderr,
        )
