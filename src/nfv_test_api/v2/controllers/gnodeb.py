"""
       Copyright 2023 Inmanta

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

from flask import request  # type: ignore
from flask_restx import Namespace, Resource  # type: ignore
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest  # type: ignore

from nfv_test_api.host import Host
from nfv_test_api.v2.controllers.common import add_model_schema
from nfv_test_api.v2.data.common import InputSafeNci
from nfv_test_api.v2.data.gnodeb import GNodeB, GNodeBCreate, GNodeBStatus
from nfv_test_api.v2.services.gnodeb import GNodeBService, GNodeBServiceHandler

namespace = Namespace(name="gnodeb", description="Basic gnodeb management")

gnodeb_model = add_model_schema(namespace, GNodeB)
gnodeb_create_model = add_model_schema(namespace, GNodeBCreate)
gnodeb_status_model = add_model_schema(namespace, GNodeBStatus)
gnodeb_service_handler = GNodeBServiceHandler()


@namespace.route("")
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class AllGNodeB(Resource):
    """
    The scope of this controller is all the gNodeBs.
    """

    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self._host = Host()
        self.gnb_service = GNodeBService(self._host, gnodeb_service_handler)

    @namespace.response(
        code=HTTPStatus.OK.value,
        description="Get all gNodeB",
        model=gnodeb_model,
        as_list=True,
    )
    def get(self):
        """
        Get all gNodeBs
        """
        return [
            gnodeb.json_dict() for gnodeb in self.gnb_service.get_all()
        ], HTTPStatus.OK

    @namespace.expect(gnodeb_create_model)
    @namespace.response(
        HTTPStatus.CREATED.value, "A new gNodeB configuration has been created", gnodeb_model
    )
    @namespace.response(
        HTTPStatus.CONFLICT.value, "Another gNodeB with the same nci already exists"
    )
    def post(self):
        """
        Create an gNodeB configuration

        The gNodeB is identified by its nci, if another gNodeB with the same nci already exists, a
        conflict error is raised.
        """
        try:
            # Validating input
            create_form = GNodeBCreate(**request.json)  # type: ignore
        except ValidationError as e:
            raise BadRequest(str(e))

        return self.gnb_service.create(create_form).json_dict(), HTTPStatus.CREATED


@namespace.route("/<nci>")
@namespace.param(
    "nci", description="The radio cell identifier, identify the cell of the gNodeB."
)
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class OneGNodeB(Resource):
    """
    The scope of this controller is a single gNodeB identified by its nci.

    With it you can either get it, create it or delete it.
    """

    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.gnb_service = GNodeBService(Host(), gnodeb_service_handler)

    @namespace.response(
        HTTPStatus.OK.value, "Found a gNodeB config with a matching nci", gnodeb_model
    )
    @namespace.response(
        HTTPStatus.NOT_FOUND.value, "Couldn't find any gNodeB with given nci"
    )
    def get(self, nci: str):
        """
        Get a gNodeB configuration

        The gNodeB is identified by its nci.
        """
        try:
            # Validating input
            InputSafeNci(nci=nci)
        except ValidationError as e:
            raise BadRequest(str(e))

        return self.gnb_service.get_one(nci).json_dict(exclude_none=True), HTTPStatus.OK

    @namespace.response(HTTPStatus.OK.value, "The gNodeB config doesn't exist anymore")
    @namespace.response(
        HTTPStatus.NOT_FOUND.value, "The gNodeB config could not be found."
    )
    @namespace.response(
        HTTPStatus.CONFLICT.value,
        "The gNodeB client should be stopped before removing config.",
    )
    def delete(self, nci: str):
        """
        Delete a gNodeB configuration.

        The gNodeB is identified by its nci. This method is idempotent, if the gNodeB
        doesn't exist it won't try to delete it again, and consider the deletion successful.
        """
        try:
            # Validating input
            InputSafeNci(nci=nci)
        except ValidationError as e:
            raise BadRequest(str(e))

        self.gnb_service.delete(nci)

        return HTTPStatus.OK


@namespace.route("/<nci>/start")
@namespace.param(
    "nci", description="The radio cell identifier, identify the cell of the gNodeB."
)
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class StartGNodeB(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.gnb_service = GNodeBService(Host(), gnodeb_service_handler)

    @namespace.response(HTTPStatus.OK.value, "gNodeB started")
    @namespace.response(
        HTTPStatus.NOT_FOUND.value, "Couldn't find any gNodeB with given nci"
    )
    @namespace.response(
        HTTPStatus.CONFLICT.value, "A gNodeB with given nci is already running"
    )
    def post(self, nci: str):
        """
        Start a gNodeB configuration

        The gNodeB is identified by its nci.
        """

        try:
            # Validating input
            InputSafeNci(nci=nci)
        except ValidationError as e:
            raise BadRequest(str(e))

        self.gnb_service.start(nci)

        return HTTPStatus.OK


@namespace.route("/<nci>/stop")
@namespace.param(
    "nci", description="The radio cell identifier, identify the cell of the gNodeB."
)
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class StopGNodeB(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.gnb_service = GNodeBService(Host(), gnodeb_service_handler)

    @namespace.response(HTTPStatus.OK.value, "gNodeB stopped")
    @namespace.response(
        HTTPStatus.NOT_FOUND.value, "Couldn't find any gNodeB with given nci"
    )
    def post(self, nci: str):
        """
        Stop a gNodeB configuration

        The gNodeB is identified by its nci.
        """

        try:
            # Validating input
            InputSafeNci(nci=nci)
        except ValidationError as e:
            raise BadRequest(str(e))

        self.gnb_service.stop(nci)

        return HTTPStatus.OK


@namespace.route("/<nci>/status")
@namespace.param(
    "nci", description="The radio cell identifier, identify the cell of the gNodeB."
)
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class StatusGNodeB(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.gnb_service = GNodeBService(Host(), gnodeb_service_handler)

    @namespace.response(
        HTTPStatus.OK.value,
        "Found a gNodeB config with a matching nci",
        gnodeb_status_model,
    )
    @namespace.response(
        HTTPStatus.NOT_FOUND.value, "Couldn't find any gNodeB with given nci"
    )
    def get(self, nci: str):
        """
        Get the status of a gNodeB.

        The gNodeB is identified by its nci.
        """

        try:
            # Validating input
            InputSafeNci(nci=nci)
        except ValidationError as e:
            raise BadRequest(str(e))

        return self.gnb_service.node_status(nci), HTTPStatus.OK
