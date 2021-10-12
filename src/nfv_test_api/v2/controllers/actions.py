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
from flask_restplus import Namespace, Resource  # type: ignore
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest  # type: ignore

from nfv_test_api.host import Host, NamespaceHost
from nfv_test_api.v2.controllers.common import add_model_schema
from nfv_test_api.v2.data.common import InputOptionalSafeName
from nfv_test_api.v2.data.ping import Ping, PingRequest
from nfv_test_api.v2.services.actions import ActionsService

namespace = Namespace(name="actions", description="Execute some actions on the host")

ping_model = add_model_schema(namespace, Ping)
ping_request_model = add_model_schema(namespace, PingRequest)


@namespace.route("/ping")
class OnePing(Resource):
    """
    The scope of this controller is the ping action on the host, not in a namespace.
    """

    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self._default_service = ActionsService(Host())
        self._interface_services: Dict[str, ActionsService] = dict()

    def get_service(self, ns_name: Optional[str]) -> ActionsService:
        if not ns_name:
            return self._default_service

        if ns_name not in self._interface_services:
            self._interface_services[ns_name] = ActionsService(NamespaceHost(ns_name))

        return self._interface_services[ns_name]

    @namespace.expect(ping_request_model)
    @namespace.response(HTTPStatus.OK, "The ping request has been executed", ping_model)
    def post(self, ns_name: Optional[str] = None):
        """
        Send ping requests to a destination

        The server will synchronously send ping requests to the required address, and them reply
        with the result.  It is the user responsibility not to set ping interval and count that would
        make the server request timeout.
        """
        try:
            # Validating input
            InputOptionalSafeName(name=ns_name)
            request_form = PingRequest(**request.json)
        except ValidationError as e:
            raise BadRequest(str(e))

        return self.get_service(ns_name).ping(request_form).json_dict(), HTTPStatus.OK


@namespace.route("/ns/<ns_name>/ping")
@namespace.param("ns_name", description="The name of the namespace in which to execute the ping")
class OnePingInNamespace(OnePing):
    """
    The scope of this controller is the ping action in a namespace on the host.

    This class is strictly equivalent to its parent one, the reason we extend it is to support
    multiple route on the same class in the generated documentation:
    https://github.com/noirbizarre/flask-restplus/issues/288
    """
