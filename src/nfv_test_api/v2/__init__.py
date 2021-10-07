from flask import Blueprint
from flask_restplus import Api

from .controllers.actions import namespace as actions_ns
from .controllers.interface import namespace as interface_ns
from .controllers.namespace import namespace as namespace_ns
from .controllers.route import namespace as route_ns

blueprint = Blueprint("api v2", __name__, url_prefix="/api/v2")

api_extension = Api(
    blueprint, title="NFV Test API", version="1.0", description="Test api for client side network operations", doc="/docs",
)

api_extension.add_namespace(namespace_ns)
api_extension.add_namespace(interface_ns)
api_extension.add_namespace(route_ns)
api_extension.add_namespace(actions_ns)
