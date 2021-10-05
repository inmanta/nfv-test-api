from flask import Blueprint
from flask_restplus import Api
from .namespace import namespace as namespace_ns
from .interface import namespace as interface_ns

blueprint = Blueprint("documented_api", __name__, url_prefix="/api/v2")

api_extension = Api(
    blueprint,
    title="Flask RESTplus Demo",
    version="1.0",
    description="Application tutorial to demonstrate Flask RESTplus extension\
        for better project structure and auto generated documentation",
    doc="/doc",
)

api_extension.add_namespace(namespace_ns)
api_extension.add_namespace(interface_ns)
