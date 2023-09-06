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
from nfv_test_api.v2.data.common import InputOptionalSafeName, InputSafeName
from nfv_test_api.v2.data.interface import (
    Interface,
    InterfaceCreate,
    InterfaceUpdate,
    LinkInfo,
)
from nfv_test_api.v2.services.bond_interface import BondInterfaceService
from nfv_test_api.v2.services.interface import InterfaceService
from nfv_test_api.v2.services.namespace import NamespaceService
from nfv_test_api.v2.services.vlan_interface import VlanInterfaceService

namespace = Namespace(name="interfaces", description="Basic interface management")

interface_model = add_model_schema(namespace, Interface)
interface_create_model = add_model_schema(namespace, InterfaceCreate)
interface_update_model = add_model_schema(namespace, InterfaceUpdate)


@namespace.route("")
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class AllInterfaces(Resource):
    """
    The scope of this controller is all the interfaces that are not in a namespace.

    With it you can either get them all, or create a new one in that scope.
    """

    def __init__(self, api=None, *args: object, **kwargs: object):
        super().__init__(api=api, *args, **kwargs)
        self._default_host = Host()
        self._hosts: Dict[str, Host] = dict()

    def get_host(self, ns_name: Optional[str]) -> Host:
        if not ns_name:
            return self._default_host

        # Ensuring the namespace exists
        NamespaceService(self._default_host).get_one(ns_name)

        if ns_name not in self._hosts:
            self._hosts[ns_name] = NamespaceHost(ns_name)

        return self._hosts[ns_name]

    @namespace.response(
        code=HTTPStatus.OK.value,
        description="Get all interfaces on the host",
        model=interface_model,
        as_list=True,
    )
    def get(self, ns_name: Optional[str] = None):
        """
        Get all interfaces on the host
        """
        try:
            # Validating input
            InputOptionalSafeName(name=ns_name)
        except ValidationError as e:
            raise BadRequest(str(e))

        return [
            interface.json_dict()
            for interface in InterfaceService(self.get_host(ns_name)).get_all()
        ], HTTPStatus.OK

    @namespace.expect(interface_create_model)
    @namespace.response(
        HTTPStatus.CREATED.value, "A new interface has been created", interface_model
    )
    @namespace.response(
        HTTPStatus.CONFLICT.value, "Another interface with the same name already exists"
    )
    def post(self, ns_name: Optional[str] = None):
        """
        Create an interface on the host

        The interface is identified by its name, if another interface with the same name already exists, a
        conflict error is raised.
        """
        try:
            # Validating input
            InputOptionalSafeName(name=ns_name)
            create_form = InterfaceCreate(**request.json)  # type: ignore
        except ValidationError as e:
            raise BadRequest(str(e))

        host = self.get_host(ns_name)
        interface_service = InterfaceService(host)
        if create_form.type == LinkInfo.Kind.BOND:
            interface_service = BondInterfaceService(host)
        if create_form.type == LinkInfo.Kind.VLAN:
            interface_service = VlanInterfaceService(host)

        return interface_service.create(create_form).json_dict(), HTTPStatus.CREATED


@namespace.route("/ns/<ns_name>")
@namespace.param(
    "ns_name", description="The name of the namespace in which interfaces belong"
)
class AllInterfacesInNamespace(AllInterfaces):
    """
    The scope of this controller is all the interfaces that are in a namespace.

    With it you can either get them all, or create a new one in that scope.

    This class is strictly equivalent to its parent one, the reason we extend it is to support
    multiple route on the same class in the generated documentation:
    https://github.com/noirbizarre/flask-restplus/issues/288
    """


@namespace.route("/<name>")
@namespace.param("name", description="The name of the interface we mean to select")
@namespace.response(
    code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
    description="An error occurred when trying to process the request, this can also be because of bad input from the user",
)
class OneInterface(Resource):
    """
    The scope of this controller is any interface that is not in a namespace.

    With it you can either get it, update it or delete it.
    """

    def __init__(self, api=None, *args: object, **kwargs: object):
        super().__init__(api=api, *args, **kwargs)
        self._default_service = InterfaceService(Host())
        self._interface_services: Dict[str, InterfaceService] = dict()

    def get_service(self, ns_name: Optional[str]) -> InterfaceService:
        if not ns_name:
            return self._default_service

        if ns_name not in self._interface_services:
            self._interface_services[ns_name] = InterfaceService(NamespaceHost(ns_name))

        return self._interface_services[ns_name]

    @namespace.response(
        HTTPStatus.OK.value, "Found an interface with a matching name", interface_model
    )
    @namespace.response(
        HTTPStatus.NOT_FOUND.value, "Couldn't find any interface with given name"
    )
    def get(self, name: str, ns_name: Optional[str] = None):
        """
        Get an interface on the host

        The interface is identified by its name.
        """
        try:
            # Validating input
            InputSafeName(name=name)
            InputOptionalSafeName(name=ns_name)
        except ValidationError as e:
            raise BadRequest(str(e))

        return (
            self.get_service(ns_name).get_one(name).json_dict(exclude_none=True),
            HTTPStatus.OK,
        )

    @namespace.expect(interface_update_model)
    @namespace.response(
        HTTPStatus.OK.value, "The interface has been updated", interface_model
    )
    @namespace.response(
        HTTPStatus.NOT_FOUND.value, "Couldn't find any interface with given name"
    )
    def patch(self, name: str, ns_name: Optional[str] = None):
        """
        Update an interface on the host

        The interface is identified by its name.
        """
        try:
            # Validating input
            InputSafeName(name=name)
            InputOptionalSafeName(name=ns_name)
            update_form = InterfaceUpdate(**request.json)  # type: ignore
        except ValidationError as e:
            raise BadRequest(str(e))
        return (
            self.get_service(ns_name).update(name, update_form).json_dict(),
            HTTPStatus.OK,
        )

    @namespace.response(HTTPStatus.OK.value, "The interface doesn't exist anymore")
    def delete(self, name: str, ns_name: Optional[str] = None):
        """
        Delete an interface from the host

        The interface is identified by its name. This method is idempotent, if the interface
        doesn't exist it won't try to delete it again, and consider the deletion successful.
        """
        try:
            # Validating input
            InputSafeName(name=name)
            InputOptionalSafeName(name=ns_name)
        except ValidationError as e:
            raise BadRequest(str(e))

        self.get_service(ns_name).delete(name)


@namespace.route("/ns/<ns_name>/<name>")
@namespace.param(
    "ns_name", description="The name of the namespace in which interfaces belong"
)
class OneInterfaceInNamespace(OneInterface):
    """
    The scope of this controller is any interface that is in a namespace.

    With it you can either get it, update it or delete it.

    This class is strictly equivalent to its parent one, the reason we extend it is to support
    multiple route on the same class in the generated documentation:
    https://github.com/noirbizarre/flask-restplus/issues/288
    """
