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
from nfv_test_api.v2.data.common import InputSafeImei
from nfv_test_api.v2.data.ue_4g import UE, UECreate, UEStatus
from nfv_test_api.v2.services.ue_4g import UEService, UEServiceHandler

namespace = Namespace(name="ue_4g", description="Basic 4G user equipment management")

ue_model = add_model_schema(namespace, UE)
ue_create_model = add_model_schema(namespace, UECreate)
ue_status_model = add_model_schema(namespace, UEStatus)
ue_service_handler = UEServiceHandler()


@namespace.route("")
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class AllUE(Resource):
    """
    The scope of this controller is all the UE.
    """

    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self._host = Host()
        self.ue_service = UEService(self._host, ue_service_handler)

    @namespace.response(
        code=HTTPStatus.OK.value,
        description="Get all UE",
        model=ue_model,
        as_list=True,
    )
    def get(self):
        """
        Get all UE
        """
        return [ue.json_dict() for ue in self.ue_service.get_all()], HTTPStatus.OK

    @namespace.expect(ue_create_model)
    @namespace.response(
        HTTPStatus.CREATED.value,
        "A new UE configuration has been created",
        ue_model,
    )
    @namespace.response(
        HTTPStatus.CONFLICT.value, "Another UE with the same imei already exists"
    )
    def post(self):
        """
        Create a UE configuration

        The UE is identified by its imei, if another ue with the same imei already exists, a
        conflict error is raised.
        """
        try:
            # Validating input
            create_form = UECreate(**request.json)  # type: ignore
        except ValidationError as e:
            raise BadRequest(str(e))

        return self.ue_service.create(create_form).json_dict(), HTTPStatus.CREATED


@namespace.route("/<imei>")
@namespace.param(
    "imei", description="The radio cell identifier, identify the cell of the UE."
)
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class OneUE(Resource):
    """
    The scope of this controller is a single UE identified by its imei.

    With it you can either get it, create it or delete it.
    """

    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.ue_service = UEService(Host(), ue_service_handler)

    @namespace.response(
        HTTPStatus.OK.value, "Found a UE config with a matching imei", ue_model
    )
    @namespace.response(
        HTTPStatus.NOT_FOUND.value, "Couldn't find any UE with given imei"
    )
    def get(self, imei: str):
        """
        Get an UE configuration

        The UE is identified by its imei.
        """
        try:
            # Validating input
            InputSafeImei(imei=imei)
        except ValidationError as e:
            raise BadRequest(str(e))

        return self.ue_service.get_one(imei).json_dict(exclude_none=True), HTTPStatus.OK

    @namespace.expect(ue_create_model)
    @namespace.response(
        HTTPStatus.OK.value, "The UE config has been created/updated", ue_model
    )
    def put(self, imei: str):
        """
        Create/Update a UE configuration

        The UE is identified by its imei.
        """
        try:
            # Validating input
            create_form = UECreate(**request.json)  # type: ignore
        except ValidationError as e:
            raise BadRequest(str(e))

        if create_form.imei != imei:
            raise BadRequest(
                f"The provided imei {imei} does not match the imei {create_form.imei} in the config."
            )

        return self.ue_service.put(create_form).json_dict(), HTTPStatus.OK

    @namespace.response(HTTPStatus.OK.value, "The UE config doesn't exist anymore")
    @namespace.response(HTTPStatus.NOT_FOUND.value, "The UE config could not be found.")
    @namespace.response(
        HTTPStatus.CONFLICT.value,
        "The UE client should be stopped before removing config.",
    )
    def delete(self, imei: str):
        """
        Delete a UE configuration.

        The UE is identified by its imei. This method is idempotent, if the UE
        doesn't exist it won't try to delete it again, and consider the deletion successful.
        """
        try:
            # Validating input
            InputSafeImei(imei=imei)
        except ValidationError as e:
            raise BadRequest(str(e))

        self.ue_service.delete(imei)

        return HTTPStatus.OK


@namespace.route("/<imei>/start")
@namespace.param(
    "imei", description="The radio cell identifier, identify the cell of the UE."
)
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class StartUE(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.ue_service = UEService(Host(), ue_service_handler)

    @namespace.response(HTTPStatus.OK.value, "UE started")
    @namespace.response(
        HTTPStatus.NOT_FOUND.value, "Couldn't find any ue with given imei"
    )
    @namespace.response(
        HTTPStatus.CONFLICT.value, "A UE with given imei is already running"
    )
    def post(self, imei: str):
        """
        Start a UE configuration

        The UE is identified by its imei.
        """

        try:
            # Validating input
            InputSafeImei(imei=imei)
        except ValidationError as e:
            raise BadRequest(str(e))

        self.ue_service.start(imei)

        return HTTPStatus.OK


@namespace.route("/<imei>/stop")
@namespace.param(
    "imei", description="The radio cell identifier, identify the cell of the UE."
)
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class StopUE(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.ue_service = UEService(Host(), ue_service_handler)

    @namespace.response(HTTPStatus.OK.value, "UE stopped")
    @namespace.response(
        HTTPStatus.NOT_FOUND.value, "Couldn't find any UE with given imei"
    )
    def post(self, imei: str):
        """
        Stop a UE configuration. If You stop the UE don't forget to restart the related eNodeB.

        The UE is identified by its imei.
        """

        try:
            # Validating input
            InputSafeImei(imei=imei)
        except ValidationError as e:
            raise BadRequest(str(e))

        self.ue_service.stop(imei)

        return HTTPStatus.OK


@namespace.route("/<imei>/status")
@namespace.param(
    "imei", description="The radio cell identifier, identify the cell of the UE."
)
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class StatusUE(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.ue_service = UEService(Host(), ue_service_handler)

    @namespace.response(
        HTTPStatus.OK.value,
        "Found a UE config with a matching imei",
        ue_status_model,
    )
    @namespace.response(
        HTTPStatus.NOT_FOUND.value, "Couldn't find any UE with given imei"
    )
    def get(self, imei: str):
        """
        Get the status of a UE.

        The UE is identified by its imei.
        """

        try:
            # Validating input
            InputSafeImei(imei=imei)
        except ValidationError as e:
            raise BadRequest(str(e))

        return self.ue_service.node_status(imei), HTTPStatus.OK
