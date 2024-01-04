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
from nfv_test_api.v2.data.common import InputSafeEnbId
from nfv_test_api.v2.data.enodeb import ENodeB, ENodeBCreate, ENodeBStatus
from nfv_test_api.v2.services.enodeb import ENodeBService, ENodeBServiceHandler

namespace = Namespace(name="enodeb", description="Basic enodeb management")

enodeb_model = add_model_schema(namespace, ENodeB)
enodeb_create_model = add_model_schema(namespace, ENodeBCreate)
enodeb_status_model = add_model_schema(namespace, ENodeBStatus)
enodeb_service_handler = ENodeBServiceHandler()


@namespace.route("")
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class AllENodeB(Resource):
    """
    The scope of this controller is all the eNodeBs.
    """

    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self._host = Host()
        self.enb_service = ENodeBService(self._host, enodeb_service_handler)

    @namespace.response(
        code=HTTPStatus.OK.value,
        description="Get all eNodeB",
        model=enodeb_model,
        as_list=True,
    )
    def get(self):
        """
        Get all eNodeBs
        """
        return [
            enodeb.json_dict() for enodeb in self.enb_service.get_all()
        ], HTTPStatus.OK

    @namespace.expect(enodeb_create_model)
    @namespace.response(
        HTTPStatus.CREATED.value,
        "A new eNodeB configuration has been created",
        enodeb_model,
    )
    @namespace.response(
        HTTPStatus.CONFLICT.value, "Another eNodeB with the same enb_id already exists"
    )
    def post(self):
        """
        Create an eNodeB configuration

        The eNodeB is identified by its enb_id, if another eNodeB with the same enb_id already exists, a
        conflict error is raised.
        """
        try:
            # Validating input
            create_form = ENodeBCreate(**request.json)  # type: ignore
        except ValidationError as e:
            raise BadRequest(str(e))

        return self.enb_service.create(create_form).json_dict(), HTTPStatus.CREATED


@namespace.route("/<enb_id>")
@namespace.param(
    "enb_id", description="The radio cell identifier, identify the cell of the eNodeB."
)
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class OneGNodeB(Resource):
    """
    The scope of this controller is a single eNodeB identified by its enb_id.

    With it you can either get it, create it or delete it.
    """

    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.enb_service = ENodeBService(Host(), enodeb_service_handler)

    @namespace.response(
        HTTPStatus.OK.value,
        "Found an eNodeB config with a matching enb_id",
        enodeb_model,
    )
    @namespace.response(
        HTTPStatus.NOT_FOUND.value, "Couldn't find any eNodeB with given enb_id"
    )
    def get(self, enb_id: str):
        """
        Get an eNodeB configuration

        The eNodeB is identified by its enb_id.
        """
        try:
            # Validating input
            InputSafeEnbId(enb_id=enb_id)
        except ValidationError as e:
            raise BadRequest(str(e))

        return (
            self.enb_service.get_one(enb_id).json_dict(exclude_none=True),
            HTTPStatus.OK,
        )

    @namespace.expect(enodeb_create_model)
    @namespace.response(
        HTTPStatus.OK.value, "The eNodeB config has been created/updated", enodeb_model
    )
    def put(self, enb_id: str):
        """
        Create/Update an eNodeB configuration

        The eNodeB is identified by its enb_id.
        """
        try:
            # Validating input
            create_form = ENodeBCreate(**request.json)  # type: ignore
        except ValidationError as e:
            raise BadRequest(str(e))

        if create_form.enb_id != enb_id:
            raise BadRequest(
                f"The provided enb_id {enb_id} does not match the enb_id {create_form.enb_id} in the config."
            )

        return self.enb_service.put(create_form).json_dict(), HTTPStatus.OK

    @namespace.response(HTTPStatus.OK.value, "The eNodeB config doesn't exist anymore")
    @namespace.response(
        HTTPStatus.NOT_FOUND.value, "The eNodeB config could not be found."
    )
    @namespace.response(
        HTTPStatus.CONFLICT.value,
        "The eNodeB client should be stopped before removing config.",
    )
    def delete(self, enb_id: str):
        """
        Delete a eNodeB configuration.

        The eNodeB is identified by its enb_id. This method is idempotent, if the eNodeB
        doesn't exist it won't try to delete it again, and consider the deletion successful.
        """
        try:
            # Validating input
            InputSafeEnbId(enb_id=enb_id)
        except ValidationError as e:
            raise BadRequest(str(e))

        self.enb_service.delete(enb_id)

        return HTTPStatus.OK


@namespace.route("/<enb_id>/start")
@namespace.param(
    "enb_id", description="The radio cell identifier, identify the cell of the eNodeB."
)
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class StartENodeB(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.enb_service = ENodeBService(Host(), enodeb_service_handler)

    @namespace.response(HTTPStatus.OK.value, "eNodeB started")
    @namespace.response(
        HTTPStatus.NOT_FOUND.value, "Couldn't find any eNodeB with given enb_id"
    )
    @namespace.response(
        HTTPStatus.CONFLICT.value, "A eNodeB with given enb_id is already running"
    )
    def post(self, enb_id: str):
        """
        Start a eNodeB configuration

        The eNodeB is identified by its enb_id.
        """

        try:
            # Validating input
            InputSafeEnbId(enb_id=enb_id)
        except ValidationError as e:
            raise BadRequest(str(e))

        self.enb_service.start(enb_id)

        return HTTPStatus.OK


@namespace.route("/<enb_id>/stop")
@namespace.param(
    "enb_id", description="The radio cell identifier, identify the cell of the eNodeB."
)
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class StopENodeB(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.enb_service = ENodeBService(Host(), enodeb_service_handler)

    @namespace.response(HTTPStatus.OK.value, "eNodeB stopped")
    @namespace.response(
        HTTPStatus.NOT_FOUND.value, "Couldn't find any eNodeB with given enb_id"
    )
    def post(self, enb_id: str):
        """
        Stop a eNodeB configuration

        The eNodeB is identified by its enb_id.
        """

        try:
            # Validating input
            InputSafeEnbId(enb_id=enb_id)
        except ValidationError as e:
            raise BadRequest(str(e))

        self.enb_service.stop(enb_id)

        return HTTPStatus.OK


@namespace.route("/<enb_id>/status")
@namespace.param(
    "enb_id", description="The radio cell identifier, identify the cell of the eNodeB."
)
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class StatusENodeB(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.enb_service = ENodeBService(Host(), enodeb_service_handler)

    @namespace.response(
        HTTPStatus.OK.value,
        "Found a eNodeB config with a matching enb_id",
        enodeb_status_model,
    )
    @namespace.response(
        HTTPStatus.NOT_FOUND.value, "Couldn't find any eNodeB with given enb_id"
    )
    def get(self, enb_id: str):
        """
        Get the status of a eNodeB.

        The eNodeB is identified by its enb_id.
        """

        try:
            # Validating input
            InputSafeEnbId(enb_id=enb_id)
        except ValidationError as e:
            raise BadRequest(str(e))

        return self.enb_service.node_status(enb_id), HTTPStatus.OK
