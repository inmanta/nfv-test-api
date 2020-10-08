import logging
import os
import re
import subprocess
from typing import List

import click
import pingparsing
import trparse
from flask import Flask, abort, jsonify, request
from flask_cors import CORS

from nfv_test_api import config, exceptions, util
from nfv_test_api.config import Route, get_config, Interface, Namespace
from nfv_test_api.util import setup_namespaces, create_namespace

app = Flask(__name__)
app.simulate = False
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
    if app.simulate:
        cfg = get_config()
        return jsonify([ns for ns in cfg.namespaces.keys()])
    return jsonify(util.list_net_ns())


@app.route("/<namespace>/", methods=["GET"])
def list_interfaces(namespace):
    if namespace is None or len(namespace) == 0:
        raise exceptions.ServerError(f"Invalid namespace {namespace}")

    if app.simulate:
        cfg = get_config()
        if namespace not in cfg.namespaces:
            return abort(404)

        return jsonify([intf.name for intf in cfg.namespaces[namespace].interfaces])

    return jsonify(util.list_interfaces(namespace))


@app.route("/<namespace>/", methods=["POST"])
def add_namespace(namespace):
    if namespace is None or len(namespace) == 0:
        raise exceptions.ServerError(f"Invalid namespace {namespace}")

    if app.simulate:
        cfg = get_config()

        if namespace in cfg.namespaces:
            return abort(409)
        cfg.namespaces[namespace] = Namespace(namespace, interfaces=[{
            "ifindex": 1,
            "ifname": "lo",
            "flags": ["LOOPBACK"],
            "mtu": 65536,
            "qdisc": "noop",
            "operstate": "DOWN",
            "linkmode": "DEFAULT",
            "group": "default",
            "txqlen": 1000,
            "link_type": "loopback",
            "address": "00:00:00:00:00:00",
            "broadcast": "00:00:00:00:00:00"
        }])
        return jsonify({})
    create_namespace(namespace)

    return jsonify({})


@app.route("/<namespace>/", methods=["DELETE"])
def delete_namespace(namespace):
    if (
        namespace is None
        or len(namespace) == 0
        or namespace not in list_namespaces().get_json()
    ):
        raise exceptions.ServerError(f"Invalid namespace {namespace}")

    interfaces: List = list_interfaces(namespace).get_json()
    untagged: List = [
        interface
        for interface in interfaces
        if "." not in interface and interface != "lo"
    ]
    if untagged:
        raise exceptions.ServerError(
            "Unable to delete namespace with untagged interfaces %s in it."
            " Move them to another interface first."
            % ", ".join(untagged)
        )

    if app.simulate:
        cfg = get_config()

        if namespace not in cfg.namespaces:
            return abort(404)

        del cfg.namespaces[namespace]
        return jsonify({})

    util.delete_namespace(namespace)
    return jsonify({})


@app.route("/<namespace>/<interface>", methods=["POST"])
def create_sub_interface(namespace, interface):
    if namespace is None or len(namespace) == 0:
        raise exceptions.ServerError(f"Invalid namespace {namespace}")

    parts = interface.split(".")
    if len(parts) not in [2, 3]:
        raise exceptions.ServerError(f"Only single and double tagged interfaces are supported")

    if app.simulate:
        cfg = get_config()
        if namespace not in cfg.namespaces:
            abort(404)

        all_interfaces = [intf.name for intf in cfg.namespaces[namespace].interfaces]
    else:
        all_interfaces = util.list_interfaces(namespace)

    if interface in all_interfaces:
        raise exceptions.ServerError(f"Interface {interface} already exists in {namespace}")

    base_interface = parts.pop(0)

    if base_interface not in all_interfaces:
        raise exceptions.ServerError(f"Base interface {base_interface} does not exist")

    outer = int(parts.pop(0))
    inner = 0
    if len(parts):
        inner = int(parts[0])

    if app.simulate:
        ns = cfg.namespaces[namespace]
        base_intf = ns.get_interface(base_interface)
        intf = config.Interface(name=interface, mac=base_intf.mac)
        ns.interfaces.append(intf)
        return jsonify({"interface": intf.get_state()})
    else:
        util.create_sub_interface(namespace, base_interface, outer, inner)
        return jsonify(util.get_interface_state(namespace, interface))


@app.route("/<namespace>/<interface>", methods=["PATCH"])
def move_interface(namespace, interface):
    if namespace is None or len(namespace) == 0:
        raise exceptions.ServerError(f"Invalid namespace {namespace}")

    parts = interface.split(".")
    if len(parts) not in range(1, 4):
        raise exceptions.ServerError(f"Only untagged, single and double tagged interfaces are supported")

    if app.simulate:
        cfg = get_config()
        if namespace not in cfg.namespaces:
            abort(404)

        all_interfaces = [intf.name for intf in cfg.namespaces[namespace].interfaces]
    else:
        all_interfaces = util.list_interfaces(namespace)

    if interface not in all_interfaces:
        raise exceptions.ServerError(f"Interface {interface} does not exist in {namespace}")

    new_namespace_key: str = "destination_namespace"
    if new_namespace_key not in request.json:
        raise exceptions.ServerError(f"Invalid request: request should contain \"destination_namespace\"")

    new_namespace = request.json[new_namespace_key]

    if app.simulate:
        old_ns: Namespace = cfg.namespaces[namespace]
        new_ns: Namespace = cfg.namespaces[new_namespace]
        iface: Interface = old_ns.get_interface(interface)
        old_ns.interfaces.remove(iface)
        new_ns.interfaces.append(iface)
    else:
        util.move_interface(new_namespace, interface, interface, old_namespace=namespace)

    return jsonify({})




@app.route("/<namespace>/<interface>", methods=["DELETE"])
def delete_sub_interface(namespace, interface):
    if namespace is None or len(namespace) == 0:
        raise exceptions.ServerError(f"Invalid namespace {namespace}")

    parts = interface.split(".")
    if len(parts) not in [2, 3]:
        raise exceptions.ServerError(f"Only single and double tagged interfaces are supported")

    if app.simulate:
        cfg = get_config()
        if namespace not in cfg.namespaces:
            abort(404)

        all_interfaces = [intf.name for intf in cfg.namespaces[namespace].interfaces]
    else:
        all_interfaces = util.list_interfaces(namespace)

    if interface not in all_interfaces:
        raise exceptions.ServerError(f"Interface {interface} dot exist in {namespace}")

    base_interface = parts.pop(0)

    if base_interface not in all_interfaces:
        raise exceptions.ServerError(f"Base interface {base_interface} does not exist")

    outer = int(parts.pop(0))
    inner = 0
    if len(parts):
        inner = int(parts[0])

    if app.simulate:
        ns = cfg.namespaces[namespace]
        intf = ns.get_interface(interface)
        ns.interfaces.remove(intf)
    else:
        util.delete_sub_interface(namespace, base_interface, outer, inner)

    return jsonify({})


@app.route("/<namespace>/<interface>/state", methods=["GET"])
def get_interface_state(namespace, interface):
    if namespace is None or len(namespace) == 0:
        raise exceptions.ServerError(f"Invalid namespace {namespace}")

    if app.simulate:
        cfg = get_config()
        if namespace not in cfg.namespaces:
            abort(404)

        ns = cfg.namespaces[namespace]
        intf = ns.get_interface(interface)
        if intf is None:
            abort(404)

        return jsonify({"interface": intf.get_state()})
    else:
        try:
            return jsonify(util.get_interface_state(namespace, interface))
        except Exception:
            LOGGER.exception("Failed to get the interface state")
            abort(404)


@app.route("/<namespace>/<interface>/state", methods=["POST"])
def set_interface_state(namespace, interface):
    if namespace is None or len(namespace) == 0:
        raise exceptions.ServerError(f"Invalid namespace {namespace}")

    if app.simulate:
        cfg = get_config()
        if namespace not in cfg.namespaces:
            abort(404)

        ns = cfg.namespaces[namespace]
        intf = ns.get_interface(interface)
        if intf is None:
            abort(404)

        intf.set_state(request.json)
        return jsonify({"interface": intf.get_state()})
    else:
        util.set_interface_state(namespace, interface, request.json)
        return jsonify(util.get_interface_state(namespace, interface))


@app.route("/<namespace>/ping", methods=["POST"])
def ping_from_ns(namespace):
    dest = request.args.get("destination")

    if app.simulate:
        if dest == "1.1.1.1":
            return jsonify(
                {
                    "destination": "1.1.1.1",
                    "packet_duplicate_count": 0,
                    "packet_duplicate_rate": 0,
                    "packet_loss_count": 0,
                    "packet_loss_rate": 0,
                    "packet_receive": 4,
                    "packet_transmit": 4,
                    "rtt_avg": 5.472,
                    "rtt_max": 10.635,
                    "rtt_mdev": 3.171,
                    "rtt_min": 2.533,
                }
            )
        else:
            return jsonify({})
    else:
        ping_parser = pingparsing.PingParsing()
        try:
            result = util.run_in_ns(namespace, ["ping", "-c", "4", "-i", "0.2", dest])
            return jsonify(ping_parser.parse(result).as_dict())
        except subprocess.CalledProcessError as e:
            LOGGER.exception("status: %s, out: %s, err: %s", e.returncode, e.stdout, e.stderr)
            return jsonify({})


@app.route("/<namespace>/traceroute", methods=["POST"])
def traceroute_from_ns(namespace):
    dest = request.args.get("destination")
    if app.simulate:
        if dest == "1.1.1.1":
            return jsonify(
                {
                    "destination_ip": "1.1.1.1",
                    "destination_name": "host",
                    "hops": [
                        {
                            "index": 1,
                            "probes": ["host (1.1.1.1) 0.013 ms", "host (1.1.1.1) 0.003 ms", "host (1.1.1.1) 0.003 ms"],
                        }
                    ],
                }
            )
        else:
            return jsonify({})
    else:
        try:
            result = util.run_in_ns(namespace, ["traceroute", dest])
            parsed = trparse.loads(result)
            hops = []
            for hop in parsed.hops:
                probes = []
                for probe in hop.probes:
                    probes.append(str(probe).strip())
                hops.append({"index": hop.idx, "probes": probes})
            traceroute = {"destination_name": parsed.dest_name, "destination_ip": parsed.dest_ip, "hops": hops}
            return jsonify(traceroute)
        except subprocess.CalledProcessError as e:
            LOGGER.exception("status: %s, out: %s, err: %s", e.returncode, e.stdout, e.stderr)
            return jsonify({})


@app.route("/<namespace>/routes", methods=["GET"])
def get_routing_table_from_ns(namespace):
    if app.simulate:
        cfg = get_config()
        if namespace not in cfg.namespaces:
            abort(404)
        ns = cfg.namespaces[namespace]
        return jsonify([route.to_json() for route in ns.routes])
    else:
        try:
            routes = util.list_routes(namespace)
            return jsonify(routes)
        except subprocess.CalledProcessError as e:
            LOGGER.exception("status: %s, out: %s, err: %s", e.returncode, e.stdout, e.stderr)
            return jsonify({})


@app.route("/<namespace>/routes", methods=["POST"])
def add_route_from_ns(namespace):
    subnet = request.get_json(force=True).get("subnet")
    gateway = request.get_json(force=True).get("gateway")
    if app.simulate:
        cfg = get_config()
        if namespace not in cfg.namespaces:
            abort(404)

        ns = cfg.namespaces[namespace]
        route = Route(subnet, gateway)
        if route in ns.routes:
            abort(409)
        else:
            ns.routes.append(route)
        return jsonify([route.to_json() for route in ns.routes])
    else:
        try:
            util.run_in_ns(namespace, ["ip", "route", "add", subnet, "via", gateway])
            routes = util.list_routes(namespace)
            return jsonify(routes)
        except subprocess.CalledProcessError as e:
            LOGGER.exception("status: %s, out: %s, err: %s", e.returncode, e.stdout, e.stderr)
            return jsonify({})


@app.route("/<namespace>/routes", methods=["DELETE"])
def delete_route_from_ns(namespace):
    subnet = request.args.get("subnet")
    gateway = request.args.get("gateway")
    if app.simulate:
        cfg = get_config()
        if namespace not in cfg.namespaces:
            abort(404)
        ns = cfg.namespaces[namespace]
        route = Route(subnet, gateway)
        if route in ns.routes:
            ns.routes.remove(route)
        else:
            abort(404)
        return jsonify([route.to_json() for route in ns.routes])
    else:
        try:
            util.run_in_ns(namespace, ["ip", "route", "del", subnet, "via", gateway])
            routes = util.list_routes(namespace)
            return jsonify(routes)
        except subprocess.CalledProcessError as e:
            LOGGER.exception("status: %s, out: %s, err: %s", e.returncode, e.stdout, e.stderr)
            return jsonify({})


@click.command()
@click.option("--config", help="The configuration file to use")
@click.option(
    "--simulate", help="Start the server in a test/mock mode. No real changes will be made to the system", is_flag=True
)
def main(config, simulate):
    cfg = get_config(config)
    setup_namespaces()
    app.simulate = simulate
    app.run(host=cfg.host, port=cfg.port)


if __name__ == "__main__":
    main()
