import logging
import os
import re

import click
import pingparsing
from flask import Flask, abort, jsonify, request
from flask_cors import CORS

from nfv_test_api import exceptions, util
from nfv_test_api.config import get_config
from nfv_test_api.util import setup_namespaces

app = Flask(__name__)
CORS(app)

# Notes:
#   * Static content available on /static


LOGGER = logging.getLogger(__name__)


@app.errorhandler(exceptions.ServerError)
def handle_invalid_usage(error):
    response = jsonify({"error": error.args[0]})
    response.status_code = 500
    return response


def get_lease_file(location, interface_name):
    return f"/var/lib/dhclient/dhclient-{location}-{interface_name}.lease"


def get_pid_file(location, interface_name):
    return f"/var/run/dhclient-{location}-{interface_name}.pid"


def get_local_dns_server(location, interface_name):
    """ Retrieve the dns server provided by the DHCP server for the given interface name
    """
    lease_file = get_lease_file(location, interface_name)
    if not os.path.exists(lease_file):
        return None

    with open(lease_file, "r") as f:
        for line in f.readlines():
            line = line.strip(" \n")
            match = re.search("option domain-name-servers (?P<ip>.*);", line)
            if match:
                return match.group("ip")
    return None


@app.route("/favicon.ico", methods=["GET"])
def not_found():
    abort(404)


@app.route("/", methods=["GET"])
def list_namespaces():
    return jsonify(util.list_net_ns())


@app.route("/<namespace>/", methods=["GET"])
def list_interfaces(namespace):
    if namespace is None or len(namespace) == 0:
        raise exceptions.ServerError(f"Invalid namespace {namespace}")
    return jsonify(util.list_interfaces(namespace))


@app.route("/<namespace>/<interface>", methods=["POST"])
def create_sub_interface(namespace, interface):
    if namespace is None or len(namespace) == 0:
        raise exceptions.ServerError(f"Invalid namespace {namespace}")

    all_interfaces = util.list_interfaces(namespace)
    if interface in all_interfaces:
        raise exceptions.ServerError(f"Interface {interface} already exists in {namespace}")

    parts = interface.split(".")
    if len(parts) not in [2, 3]:
        raise exceptions.ServerError(f"Only single and double tagged interfaces are supported")

    base_interface = parts.pop(0)

    if base_interface not in all_interfaces:
        raise exceptions.ServerError(f"Base interface {base_interface} does not exist")

    outer = int(parts.pop(0))
    inner = 0
    if len(parts):
        inner = int(parts[0])

    util.create_sub_interface(namespace, base_interface, outer, inner)

    return jsonify(util.get_interface_state(namespace, interface))


@app.route("/<namespace>/<interface>", methods=["DELETE"])
def delete_sub_interface(namespace, interface):
    if namespace is None or len(namespace) == 0:
        raise exceptions.ServerError(f"Invalid namespace {namespace}")

    all_interfaces = util.list_interfaces(namespace)
    if interface not in all_interfaces:
        raise exceptions.ServerError(f"Interface {interface} dot exist in {namespace}")

    parts = interface.split(".")
    if len(parts) not in [2, 3]:
        raise exceptions.ServerError(f"Only single and double tagged interfaces are supported")

    base_interface = parts.pop(0)

    if base_interface not in all_interfaces:
        raise exceptions.ServerError(f"Base interface {base_interface} does not exist")

    outer = int(parts.pop(0))
    inner = 0
    if len(parts):
        inner = int(parts[0])

    util.delete_sub_interface(namespace, base_interface, outer, inner)

    return jsonify({})


@app.route("/<namespace>/<interface>/state", methods=["GET"])
def get_interface_state(namespace, interface):
    if namespace is None or len(namespace) == 0:
        raise exceptions.ServerError(f"Invalid namespace {namespace}")

    try:
        return jsonify(util.get_interface_state(namespace, interface))
    except Exception:
        LOGGER.exception("Failed to get the interface state")
        abort(404)


@app.route("/<namespace>/<interface>/state", methods=["POST"])
def set_interface_state(namespace, interface):
    util.set_interface_state(namespace, interface, request.json)
    return jsonify(util.get_interface_state(namespace, interface))


@app.route("/<namespace>/ping", methods=["POST"])
def ping_from_ns(namespace):
    dest = request.args.get("destination")
    ping_parser = pingparsing.PingParsing()
    result = util.run_in_ns(namespace, ["ping", "-c", "4", "-i", "0.2", dest])
    return jsonify(ping_parser.parse(result).as_dict())


@click.command()
@click.option("--config", help="The configuration file to use")
def main(config):
    cfg = get_config(config)
    setup_namespaces()
    app.run(host=cfg.host, port=cfg.port)


if __name__ == "__main__":
    main()
