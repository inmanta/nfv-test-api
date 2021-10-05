from flask import request
from flask_restplus import Namespace, Resource
from nfv_test_api.services.interface import InterfaceService
from nfv_test_api.host import Host
from nfv_test_api import data
from http import HTTPStatus
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest

namespace = Namespace(name="interfaces", description="Basic interface management")

interface_model = namespace.schema_model(name="Interface", schema=data.Interface.schema())
interface_create_model = namespace.schema_model(name="InterfaceCreate", schema=data.Interface.CreateForm.schema())
interface_update_model = namespace.schema_model(name="InterfaceUpdate", schema=data.Interface.UpdateForm.schema())

@namespace.route("")
class All(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.host = Host()
        self.service = InterfaceService(self.host)

    @namespace.response(code=HTTPStatus.OK, description="Get all interfaces on the host", model=interface_model, as_list=True)
    def get(self):
        return [interface.json_dict() for interface in self.service.get_all()], HTTPStatus.OK

    @namespace.expect(interface_create_model)
    @namespace.response(HTTPStatus.CREATED, "A new interface has been created", interface_model)
    @namespace.response(HTTPStatus.CONFLICT, "Another interface with the same name already exists")
    def post(self):
        try:
            create_form = data.Interface.CreateForm(**request.json)
        except ValidationError as e:
            raise BadRequest(str(e))
        return self.service.create(create_form).json_dict(), HTTPStatus.CREATED


@namespace.route("/<name>")
class One(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api=api, *args, **kwargs)
        self.host = Host()
        self.service = InterfaceService(self.host)

    @namespace.response(HTTPStatus.OK, "Found an interface with a matching name", interface_model)
    @namespace.response(HTTPStatus.NOT_FOUND, "Couldn't find any interface with given name")
    def get(self, name: str):
        try:
            data.InputSafeName(name=name)
        except ValidationError as e:
            raise BadRequest(str(e))

        return self.service.get(name).json_dict(exclude_none=True), HTTPStatus.OK

    @namespace.expect(interface_update_model)
    @namespace.response(HTTPStatus.OK, "The interface has been updated", interface_model)
    def post(self, name: str):
        try:
            data.InputSafeName(name=name)
            update_form = data.Interface.UpdateForm(**request.json)
        except ValidationError as e:
            raise BadRequest(str(e))
        return self.service.create(update_form).json_dict(), HTTPStatus.OK

    @namespace.response(HTTPStatus.OK, "The interface doesn't exist anymore")
    def delete(self, name: str):
        try:
            data.InputSafeName(name=name)
        except ValidationError as e:
            raise BadRequest(str(e))

        self.service.delete(name)
