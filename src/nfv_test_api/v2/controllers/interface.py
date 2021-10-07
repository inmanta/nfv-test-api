from http import HTTPStatus
from typing import Dict, Optional

from flask import request
from flask_restplus import Namespace, Resource
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest

from nfv_test_api.host import Host, NamespaceHost
from nfv_test_api.v2 import data
from nfv_test_api.v2.controllers.common import add_model_schema
from nfv_test_api.v2.services import BondInterfaceService, InterfaceService

namespace = Namespace(name="interfaces", description="Basic interface management")

interface_model = add_model_schema(namespace, data.Interface)
interface_create_model = add_model_schema(namespace, data.InterfaceCreate)
interface_update_model = add_model_schema(namespace, data.InterfaceUpdate)


@namespace.route("")
class AllInterfaces(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self._default_host = Host()
        self._hosts: Dict[str, Host] = dict()

    def get_host(self, ns_name: Optional[str]) -> Host:
        if not ns_name:
            return self._default_host

        if ns_name not in self._hosts:
            self._hosts[ns_name] = NamespaceHost(ns_name)

        return self._hosts[ns_name]

    @namespace.response(code=HTTPStatus.OK, description="Get all interfaces on the host", model=interface_model, as_list=True)
    def get(self, ns_name: Optional[str] = None):
        try:
            # Validating input
            data.InputOptionalSafeName(name=ns_name)
        except ValidationError as e:
            raise BadRequest(str(e))

        return [interface.json_dict() for interface in InterfaceService(self.get_host(ns_name)).get_all()], HTTPStatus.OK

    @namespace.expect(interface_create_model)
    @namespace.response(HTTPStatus.CREATED, "A new interface has been created", interface_model)
    @namespace.response(HTTPStatus.CONFLICT, "Another interface with the same name already exists")
    def post(self, ns_name: Optional[str] = None):
        try:
            # Validating input
            data.InputOptionalSafeName(name=ns_name)
            create_form = data.InterfaceCreate(**request.json)
        except ValidationError as e:
            raise BadRequest(str(e))

        host = self.get_host(ns_name)
        interface_service = InterfaceService(host)
        if create_form.type == data.LinkInfo.Kind.BOND:
            interface_service = BondInterfaceService(host)

        return interface_service.create(create_form).json_dict(), HTTPStatus.CREATED


@namespace.route("/ns/<ns_name>")
class AllInterfacesInNamespace(AllInterfaces):
    pass


@namespace.route("/<name>")
class OneInterface(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self._default_service = InterfaceService(Host())
        self._interface_services: Dict[str, InterfaceService] = dict()

    def get_service(self, ns_name: Optional[str]) -> InterfaceService:
        if not ns_name:
            return self._default_service

        if ns_name not in self._interface_services:
            self._interface_services[ns_name] = InterfaceService(NamespaceHost(ns_name))

        return self._interface_services[ns_name]

    @namespace.response(HTTPStatus.OK, "Found an interface with a matching name", interface_model)
    @namespace.response(HTTPStatus.NOT_FOUND, "Couldn't find any interface with given name")
    def get(self, name: str, ns_name: Optional[str] = None):
        try:
            # Validating input
            data.InputSafeName(name=name)
            data.InputOptionalSafeName(name=ns_name)
        except ValidationError as e:
            raise BadRequest(str(e))

        return self.get_service(ns_name).get(name).json_dict(exclude_none=True), HTTPStatus.OK

    @namespace.expect(interface_update_model)
    @namespace.response(HTTPStatus.OK, "The interface has been updated", interface_model)
    def patch(self, name: str, ns_name: Optional[str] = None):
        try:
            # Validating input
            data.InputSafeName(name=name)
            data.InputOptionalSafeName(name=ns_name)
            update_form = data.InterfaceUpdate(**request.json)
        except ValidationError as e:
            raise BadRequest(str(e))
        return self.get_service(ns_name).update(name, update_form).json_dict(), HTTPStatus.OK

    @namespace.response(HTTPStatus.OK, "The interface doesn't exist anymore")
    def delete(self, name: str, ns_name: Optional[str] = None):
        try:
            # Validating input
            data.InputSafeName(name=name)
            data.InputOptionalSafeName(name=ns_name)
        except ValidationError as e:
            raise BadRequest(str(e))

        self.get_service(ns_name).delete(name)


@namespace.route("/ns/<ns_name>/<name>")
class OneInterfaceInNamespace(OneInterface):
    pass
