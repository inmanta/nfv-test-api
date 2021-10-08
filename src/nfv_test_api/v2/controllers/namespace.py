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

from flask import request  # type: ignore
from flask_restplus import Namespace as ApiNamespace  # type: ignore
from flask_restplus import Resource
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest  # type: ignore

from nfv_test_api.host import Host
from nfv_test_api.v2.controllers.common import add_model_schema
from nfv_test_api.v2.data.common import InputSafeName
from nfv_test_api.v2.data.namespace import Namespace, NamespaceCreate
from nfv_test_api.v2.services.namespace import NamespaceService

namespace = ApiNamespace(name="namespaces", description="Basic namespace management")

namespace_model = add_model_schema(namespace, Namespace)
namespace_create_model = add_model_schema(namespace, NamespaceCreate)


@namespace.route("")
class AllNamespaces(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.host = Host()
        self.service = NamespaceService(self.host)

    @namespace.response(code=HTTPStatus.OK, description="Get all namespaces on the host", model=namespace_model, as_list=True)
    def get(self):
        return [namespace.json_dict() for namespace in self.service.get_all()], HTTPStatus.OK

    @namespace.expect(namespace_create_model)
    @namespace.response(HTTPStatus.CREATED, "A new namespace has been created", namespace_model)
    @namespace.response(HTTPStatus.CONFLICT, "Another namespace with the same name already exists")
    def post(self):
        try:
            create_form = NamespaceCreate(**request.json)
        except ValidationError as e:
            raise BadRequest(str(e))
        return self.service.create(create_form).json_dict(), HTTPStatus.CREATED


@namespace.route("/<name>")
class OneNamespace(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.host = Host()
        self.service = NamespaceService(self.host)

    @namespace.response(HTTPStatus.OK, "Found a namespace with a matching name", namespace_model)
    @namespace.response(HTTPStatus.NOT_FOUND, "Couldn't find any namespace with given name")
    def get(self, name: str):
        try:
            InputSafeName(name=name)
        except ValidationError as e:
            raise BadRequest(str(e))

        return self.service.get_one(name).json_dict(), HTTPStatus.OK

    @namespace.response(HTTPStatus.OK, "The namespace doesn't exist anymore")
    def delete(self, name: str):
        try:
            InputSafeName(name=name)
        except ValidationError as e:
            raise BadRequest(str(e))

        self.service.delete(name)
