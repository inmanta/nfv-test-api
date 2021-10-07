from http import HTTPStatus
from typing import Dict, Optional

from flask_restplus import Namespace, Resource
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest

from nfv_test_api.host import Host, NamespaceHost
from nfv_test_api.v2 import data
from nfv_test_api.v2.controllers.common import add_model_schema
from nfv_test_api.v2.services import RouteService

namespace = Namespace(name="routes", description="Basic route management")

route_model = add_model_schema(namespace, data.Route)


@namespace.route("")
class AllRoutes(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self._default_service = RouteService(Host())
        self._route_services: Dict[str, RouteService] = dict()

    def get_service(self, ns_name: Optional[str]) -> RouteService:
        if not ns_name:
            return self._default_service

        if ns_name not in self._route_services:
            self._route_services[ns_name] = RouteService(NamespaceHost(ns_name))

        return self._route_services[ns_name]

    @namespace.response(code=HTTPStatus.OK, description="Get all routes on the host", model=route_model, as_list=True)
    def get(self, ns_name: Optional[str] = None):
        try:
            # Validating input
            data.InputOptionalSafeName(name=ns_name)
        except ValidationError as e:
            raise BadRequest(str(e))

        return [route.json_dict() for route in self.get_service(ns_name).get_all()], HTTPStatus.OK


@namespace.route("/ns/<ns_name>")
class AllRoutesInNamespace(AllRoutes):
    pass


@namespace.route("/<dst_addr>")
class OneRoute(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self._default_service = RouteService(Host())
        self._route_services: Dict[str, RouteService] = dict()

    def get_service(self, ns_name: Optional[str]) -> RouteService:
        if not ns_name:
            return self._default_service

        if ns_name not in self._route_services:
            self._route_services[ns_name] = RouteService(NamespaceHost(ns_name))

        return self._route_services[ns_name]

    @namespace.response(HTTPStatus.OK, "Found an route with a matching destination", route_model)
    @namespace.response(HTTPStatus.NOT_FOUND, "Couldn't find any route with given destination")
    def get(self, dst_addr: str, dst_prefix_len: Optional[int] = None, ns_name: Optional[str] = None):
        try:
            # Validating input
            destination = data.InputDestination(dst_addr=dst_addr, dst_prefix_len=dst_prefix_len).destination_name
            data.InputOptionalSafeName(name=ns_name)
        except ValidationError as e:
            raise BadRequest(str(e))

        return self.get_service(ns_name).get(destination).json_dict(exclude_none=True), HTTPStatus.OK


@namespace.route("/<dst_addr>/<int:dst_prefix_len>")
class OnRouteWithPrefix(OneRoute):
    pass


@namespace.route("/ns/<ns_name>/<dst_addr>")
class OneRouteInNamespace(OneRoute):
    pass


@namespace.route("/ns/<ns_name>/<dst_addr>/<int:dst_prefix_len>")
class OneRouteWithPrefixInNamespace(OneRoute):
    pass
