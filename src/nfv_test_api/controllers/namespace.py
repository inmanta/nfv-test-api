from flask import request
from flask_restplus import Namespace, Resource
from nfv_test_api.services.namespace import NamespaceService
from nfv_test_api.host import Host
from nfv_test_api import data
from http import HTTPStatus
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest

namespace = Namespace(name="namespaces", description="Basic namespace management")

namespace_model = namespace.schema_model(name="Namespace", schema=data.Namespace.schema())
namespace_create_model = namespace.schema_model(name="NamespaceCreate", schema=data.Namespace.CreateForm.schema())

@namespace.route("")
class All(Resource):
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
            create_form = data.Namespace.CreateForm(**request.json)
        except ValidationError as e:
            raise BadRequest(str(e))
        return self.service.create(create_form).json_dict(), HTTPStatus.CREATED


@namespace.route("/<name>")
class One(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.host = Host()
        self.service = NamespaceService(self.host)

    @namespace.response(HTTPStatus.OK, "Found a namespace with a matching name", namespace_model)
    @namespace.response(HTTPStatus.NOT_FOUND, "Couldn't find any namespace with given name")
    def get(self, name: str):
        try:
            data.InputSafeName(name=name)
        except ValidationError as e:
            raise BadRequest(str(e))

        return self.service.get(name).json_dict(), HTTPStatus.OK

    @namespace.response(HTTPStatus.OK, "The namespace doesn't exist anymore")
    def delete(self, name: str):
        try:
            data.InputSafeName(name=name)
        except ValidationError as e:
            raise BadRequest(str(e))

        self.service.delete(name)
