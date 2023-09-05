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
from http import HTTPStatus
from typing import Dict, Optional

from flask import request  # type: ignore
from flask_restx import Namespace, Resource  # type: ignore
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest  # type: ignore

from nfv_test_api.host import Host, NamespaceHost
from nfv_test_api.v2.controllers.common import add_model_schema
from nfv_test_api.v2.data.common import InputOptionalSafeName
from nfv_test_api.v2.data.route import InputDestination, Route, RouteCreate, RouteUpdate
from nfv_test_api.v2.services.namespace import NamespaceService
from nfv_test_api.v2.services.route import RouteService

namespace = Namespace(name="routes", description="Read routes on the host")

route_model = add_model_schema(namespace, Route)
route_create_model = add_model_schema(namespace, RouteCreate)
route_update_model = add_model_schema(namespace, RouteUpdate)


@namespace.route("")
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class AllRoutes(Resource):
    """
    The scope of this controller is all the routes that are not in a namespace.

    With it you can get them all.
    """

    def __init__(self, api=None, *args: object, **kwargs: object):
        super().__init__(api=api, *args, **kwargs)
        self._default_service = RouteService(Host())
        self._route_services: Dict[str, RouteService] = dict()

    def get_service(self, ns_name: Optional[str]) -> RouteService:
        if not ns_name:
            return self._default_service

        # Ensuring the namespace exists
        NamespaceService(Host()).get_one(ns_name)

        if ns_name not in self._route_services:
            self._route_services[ns_name] = RouteService(NamespaceHost(ns_name))

        return self._route_services[ns_name]

    @namespace.response(
        code=HTTPStatus.OK,
        description="Get all routes on the host",
        model=route_model,
        as_list=True,
    )
    def get(self, ns_name: Optional[str] = None):
        """
        Get all routes on the host
        """
        try:
            # Validating input
            InputOptionalSafeName(name=ns_name)
        except ValidationError as e:
            raise BadRequest(str(e))

        return [
            route.json_dict() for route in self.get_service(ns_name).get_all()
        ], HTTPStatus.OK

    @namespace.expect(route_create_model)
    @namespace.response(
        HTTPStatus.CREATED.value, "A new route has been created", route_model
    )
    @namespace.response(
        HTTPStatus.CONFLICT, "Another route with the same name already exists"
    )
    @namespace.response(
        HTTPStatus.UNPROCESSABLE_ENTITY,
        "Couldn't update route because of invalid input",
    )
    def post(self, ns_name: Optional[str] = None):
        """
        Create a route on the host

        The route is identified by its destination address, if another route with the same destination
        already exists, a conflict error is raised.
        """
        try:
            # Validating input
            InputOptionalSafeName(name=ns_name)
            create_form = RouteCreate(**request.json)  # type: ignore
        except ValidationError as e:
            raise BadRequest(str(e))

        return (
            self.get_service(ns_name).create(create_form).json_dict(),
            HTTPStatus.CREATED,
        )


@namespace.route("/ns/<ns_name>")
@namespace.param(
    "ns_name", description="The name of the namespace in which routes belong"
)
class AllRoutesInNamespace(AllRoutes):
    """
    The scope of this controller is all the routes that are in a namespace.

    With it you can get them all.

    This class is strictly equivalent to its parent one, the reason we extend it is to support
    multiple route on the same class in the generated documentation:
    https://github.com/noirbizarre/flask-restplus/issues/288
    """


@namespace.route("/<dst_addr>")
@namespace.param(
    "dst_addr",
    description='The destination ("default" or any address with a prefix length) of the route we mean to select',
)
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class OneRoute(Resource):
    """
    The scope of this controller is any route that is not in a namespace.

    With it you can get it.
    """

    def __init__(self, api=None, *args: object, **kwargs: object):
        super().__init__(api=api, *args, **kwargs)
        self._default_service = RouteService(Host())
        self._route_services: Dict[str, RouteService] = dict()

    def get_service(self, ns_name: Optional[str]) -> RouteService:
        if not ns_name:
            return self._default_service

        if ns_name not in self._route_services:
            self._route_services[ns_name] = RouteService(NamespaceHost(ns_name))

        return self._route_services[ns_name]

    @namespace.response(
        HTTPStatus.OK, "Found an route with a matching destination", route_model
    )
    @namespace.response(
        HTTPStatus.NOT_FOUND, "Couldn't find any route with given destination"
    )
    def get(
        self,
        dst_addr: str,
        dst_prefix_len: Optional[int] = None,
        ns_name: Optional[str] = None,
    ):
        """
        Get a route on the host

        The route is identified by its destination.
        """
        try:
            # Validating input
            destination = InputDestination(
                dst_addr=dst_addr,  # type: ignore
                dst_prefix_len=dst_prefix_len,  # type: ignore
            ).destination_name
            InputOptionalSafeName(name=ns_name)
        except ValidationError as e:
            raise BadRequest(str(e))

        return (
            self.get_service(ns_name).get_one(destination).json_dict(exclude_none=True),
            HTTPStatus.OK,
        )

    @namespace.expect(route_update_model)
    @namespace.response(HTTPStatus.OK.value, "The route has been updated", route_model)
    @namespace.response(
        HTTPStatus.NOT_FOUND, "Couldn't find any route with given destination address"
    )
    @namespace.response(
        HTTPStatus.UNPROCESSABLE_ENTITY,
        "Couldn't update route because of invalid input",
    )
    def patch(
        self,
        dst_addr: str,
        dst_prefix_len: Optional[int] = None,
        ns_name: Optional[str] = None,
    ):
        """
        Update a route on the host

        The route is identified by its destination.
        """
        try:
            # Validating input
            destination = InputDestination(
                dst_addr=dst_addr,  # type: ignore
                dst_prefix_len=dst_prefix_len,  # type: ignore
            ).destination_name
            InputOptionalSafeName(name=ns_name)
            update_form = RouteUpdate(**request.json)  # type: ignore
        except ValidationError as e:
            raise BadRequest(str(e))

        return (
            self.get_service(ns_name)
            .update(destination, update_form)
            .json_dict(exclude_none=True),
            HTTPStatus.OK,
        )

    @namespace.response(HTTPStatus.OK.value, "The route doesn't exist anymore")
    def delete(
        self,
        dst_addr: str,
        dst_prefix_len: Optional[int] = None,
        ns_name: Optional[str] = None,
    ):
        """
        Delete a route from the host

        The route is identified by its destination. This method is idempotent, if the route
        doesn't exist it won't try to delete it again, and consider the deletion successful.
        """
        try:
            # Validating input
            destination = InputDestination(
                dst_addr=dst_addr,  # type: ignore
                dst_prefix_len=dst_prefix_len,  # type: ignore
            ).destination_name
            InputOptionalSafeName(name=ns_name)
        except ValidationError as e:
            raise BadRequest(str(e))

        self.get_service(ns_name).delete(destination)


@namespace.route("/<dst_addr>/<int:dst_prefix_len>")
@namespace.param("dst_addr", description="The address of the destination of the route")
@namespace.param(
    "dst_prefix_len", description="The prefix length of the destination of the route"
)
class OneRouteWithPrefix(OneRoute):
    """
    The scope of this controller is any route that is not in a namespace.

    With it you can get it.

    The class is identical to its superclass OneRoute, but can match destination addresses
    (and not just "default")

    This class is strictly equivalent to its parent one, the reason we extend it is to support
    multiple route on the same class in the generated documentation:
    https://github.com/noirbizarre/flask-restplus/issues/288
    """


@namespace.route("/ns/<ns_name>/<dst_addr>")
@namespace.param(
    "ns_name", description="The name of the namespace in which the route belong"
)
class OneRouteInNamespace(OneRoute):
    """
    The scope of this controller is any route that is in a namespace.

    With it you can get it.

    This class is strictly equivalent to its parent one, the reason we extend it is to support
    multiple route on the same class in the generated documentation:
    https://github.com/noirbizarre/flask-restplus/issues/288
    """


@namespace.route("/ns/<ns_name>/<dst_addr>/<int:dst_prefix_len>")
@namespace.param(
    "ns_name", description="The name of the namespace in which the route belong"
)
class OneRouteWithPrefixInNamespace(OneRouteWithPrefix, OneRouteInNamespace):
    """
    The scope of this controller is any route that is in a namespace.

    With it you can get it.

    The class is identical to its superclass OneRouteInNamespace, but can match destination
    addresses (and not just "default")

    This class is strictly equivalent to its parent one, the reason we extend it is to support
    multiple route on the same class in the generated documentation:
    https://github.com/noirbizarre/flask-restplus/issues/288
    """
