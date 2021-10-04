from typing import List, Optional
from nfv_test_api.controllers.base_controller import BaseController
from nfv_test_api.data import CommandStatus, Route
from nfv_test_api.host import Host
from pydantic import ValidationError
import json
import logging


LOGGER = logging.getLogger(__name__)


class RouteController(BaseController[Route]):
    def __init__(self, host: Host) -> None:
        super().__init__(host)

    def get_all_raw(self) -> List[object]:
        stdout, stderr = self.host.exec(["ip", "-j", "-details", "route"])
        if stderr:
            raise RuntimeError(f"Failed to run route command on host: {stderr}")

        raw_routes = json.loads(stdout or "[]")
        if not isinstance(raw_routes, list):
            raise RuntimeError(
                f"Failed to parse the list of routes.  Expected a list but got a {type(raw_routes)}: "
                f"{raw_routes}"
            )

        return raw_routes

    def get_all(self) -> List[Route]:
        routes: List[Route] = []
        for raw_route in self.get_all_raw():
            try:
                routes.append(Route(**raw_route))
            except ValidationError as e:
                LOGGER.error(f"Failed to parse a route: {raw_route}\n" f"{str(e)}")

        return routes

    def get(self, identifier: str) -> Optional[Route]:
        for route in self.get_all():
            if route.dst == identifier:
                return route
            
        return None

    def create(self, o: Route.CreateForm) -> Route:
        return super().create(o)

    def update(self, identifier: str, o: Route.UpdateForm) -> Route:
        return super().update(identifier, o)

    def delete(self, identifier: str) -> None:
        return super().delete(identifier)

    def status(self) -> CommandStatus:
        command = ["ip", "-details", "route"]
        stdout, stderr = self.host.exec(command)

        return CommandStatus(
            command=command,
            stdout=stdout,
            stderr=stderr,
        )
