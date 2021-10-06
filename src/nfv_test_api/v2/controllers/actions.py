from http import HTTPStatus
from typing import Dict, Optional

from flask import request
from flask_restplus import Namespace, Resource
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest

from nfv_test_api.host import Host, NamespaceHost
from nfv_test_api.v2 import data
from nfv_test_api.v2.controllers.common import add_model_schema
from nfv_test_api.v2.services.actions import ActionsService

namespace = Namespace(name="actions", description="Execute some actions on the host")

ping_model = add_model_schema(namespace, data.Ping)
ping_request_model = add_model_schema(namespace, data.PingRequest)


@namespace.route("/ping")
@namespace.route("/ns/<ns_name>/ping")
class Ping(Resource):
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
        try:
            # Validating input
            data.InputOptionalSafeName(name=ns_name)
            request_form = data.PingRequest(**request.json)
        except ValidationError as e:
            raise BadRequest(str(e))

        return self.get_service(ns_name).ping(request_form).json_dict(), HTTPStatus.OK

