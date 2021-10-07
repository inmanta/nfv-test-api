import json
import logging
from typing import List, Union

from pydantic import ValidationError
from werkzeug.exceptions import NotFound

from nfv_test_api.host import Host
from nfv_test_api.v2.data import CommandStatus, Route, RouteCreate, RouteUpdate

from .base_service import BaseService, K

LOGGER = logging.getLogger(__name__)


class RouteService(BaseService[Route]):
    def __init__(self, host: Host) -> None:
        super().__init__(host)

    def get_all_raw(self) -> List[object]:
        stdout, stderr = self.host.exec(["ip", "-j", "-details", "route"])
        if stderr:
            raise RuntimeError(f"Failed to run route command on host: {stderr}")

        raw_routes = json.loads(stdout or "[]")
        if not isinstance(raw_routes, list):
            raise RuntimeError(
                f"Failed to parse the list of routes.  Expected a list but got a {type(raw_routes)}: " f"{raw_routes}"
            )

        return raw_routes

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

    def get_or_default(self, identifier: str, default: K = None) -> Union[Route, K]:
        for route in self.get_all():
            if str(route.dst) == identifier:
                return route

        return default

    def get(self, identifier: str) -> Route:
        route = self.get_or_default(identifier)
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

        return CommandStatus(command=command, stdout=stdout, stderr=stderr,)
