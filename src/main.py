from flask import Flask, request
from functools import lru_cache
from collections import defaultdict
import yaml
import os
import subprocess
import re
import json
from flask import jsonify

app = Flask(__name__)

# Notes:
#   * Static content available on /static


class ServerError(Exception):
    pass


@app.errorhandler(ServerError)
def handle_invalid_usage(error):
    response = jsonify({"error": error.args[0]})
    response.status_code = 500
    return response

@lru_cache(maxsize=1)
def get_config():
    path_config_file = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    with open(path_config_file, 'r') as stream:
        return yaml.safe_load(stream)


def get_mapping_to_namespace_ids():
    result = {}
    output = subprocess.check_output(args=["ip", "netns", "list"]).decode()
    for line in output.split('\n'):
        line = line.strip()
        if line:
            m = re.search("(?P<namespace>LOC\d+) \(id: (?P<identifier>\d+)\)", line)
            if m is None:
                raise Exception(f"Failed to extract network namespace id from \"{line}\"")
            namespace = m.group("namespace")
            identifier = m.group("identifier")
            result[namespace] = identifier
    return result


def get_lease_file(interface_name):
    return f"/var/lib/dhclient/dhclient--{interface_name}.lease"


def get_pid_file(interface_name):
    return f"/var/run/dhclient-{interface_name}.pid"


def get_local_dns_server(interface_name):
    lease_file = get_lease_file(interface_name)
    if not os.path.exists(lease_file):
        return None
    with open(lease_file, "r") as f:
        for line in f.readlines():
            line = line.strip(' \n')
            match = re.search("option domain-name-servers (?P<ip>.*);", line)
            if match:
                return match.group("ip")
    return None


@app.route('/addresses', methods=["GET"])
def addresses():
    config = get_config()
    namespace_to_id_map = get_mapping_to_namespace_ids()
    result = defaultdict(dict)
    for namespace, identifier in namespace_to_id_map.items():
        result[namespace]["namespace_id"] = identifier
        interface_name = config["locations"][namespace]
        result[namespace]["interface"] = interface_name
        result[namespace]["local_dns_servers"] = get_local_dns_server(interface_name)
    return result


@app.route('/interface/<loc>', methods=["GET", "POST"])
def interface(loc):
    if request.method == "GET":
        return get_interface_state(loc)
    else:
        if "new_state" not in request.form:
            raise ServerError("Parameter 'new_state' is missing in form")
        new_state = request.form["new_state"]
        set_interface_state(loc, new_state)
        return "ok"


def set_interface_state(loc, new_status):
    new_status = new_status.lower()
    if new_status not in ["up", "down"]:
        raise Exception(f"Invalid new_state: {new_status}")

    # Set administrative state
    interface = get_config()["locations"][loc]
    args = ["ip", "netns", "exec", loc, "ip", "link", "set", "dev", interface, new_status]
    try:
        subprocess.check_output(args=args).decode()
    except subprocess.CalledProcessError:
        raise Exception(f"Failed to set state of interface {interface} to {new_status} (location={loc})")

    if new_status == "up":
        start_dhclient(loc, interface)
    else:
        remove_ips_from_interface(loc, interface)


def remove_ips_from_interface(loc, interface_name):
    pid_file = get_pid_file(interface_name)
    lease_file = get_lease_file(interface_name)
    bash_command = ["bash", "-c", f"pkill -F {pid_file} && rm -f {pid_file} {lease_file} && ip addr flush dev {interface_name}"]
    args = ["ip", "netns", "exec", loc] + bash_command
    try:
        subprocess.check_output(args=args).decode()
    except subprocess.CalledProcessError:
        raise Exception(f"Failed to remove ips from {interface_name} (location={loc})")


def start_dhclient(loc, interface_name):
    # Start dhclient
    pid_file = get_pid_file(interface_name)
    lease_file = get_lease_file(interface_name)
    args = ["ip", "netns", "exec", loc, "/sbin/dhclient", "-1", "-q", "-lf", lease_file, "-pf", pid_file, interface_name]
    try:
        subprocess.check_output(args=args).decode()
    except subprocess.CalledProcessError:
        raise Exception(f"Failed to start dhclient (location={loc})")


def get_interface_state(loc):
    interface = get_config()["locations"][loc]
    args = ["ip", "netns", "exec", loc, "ip", "addr", "ls", "dev", interface]
    try:
        output = subprocess.check_output(args=args).decode()
    except subprocess.CalledProcessError:
        raise Exception(f"Failed to list addresses on interface {interface} (location={loc})")
    result = {"addresses": []}
    for line in output.split('\n'):
        line = line.strip(' ')
        match = re.search("(inet|inet6) (?P<ip>\S*) .*", line)
        if match:
            ip = match.group("ip")
            result["addresses"].append(ip)
    return result


@app.route('/dns-lookup/<loc>/<dns_server>', methods=["GET"])
def dns_lookup(loc, dns_server):
    hostname_dns_lookup = get_config()["hostname_for_dns_lookup"]
    timeout_in_sec = get_config()["connection_config"]["timeout_dns_lookup_in_ms"] / 1000
    args = ["ip", "netns", "exec", loc, "dig", f"@{dns_server}", "+noall", "+answer", "+stats", hostname_dns_lookup, "A"]
    try:
        output = subprocess.check_output(timeout=timeout_in_sec, args=args).decode()
    except subprocess.TimeoutExpired:
        raise ServerError(f"Timeout occured while executing DNS lookup for {hostname_dns_lookup} on DNS server {dns_server} "
                        f"(location={loc})")
    except subprocess.CalledProcessError:
        raise ServerError(f"Failed to execute DNS lookup for {hostname_dns_lookup} on DNS server {dns_server} (location={loc})")
    a_records = []
    query_time = None
    for line in output.split('\n'):
        line = line.strip()
        # Empty line
        if not line:
            continue
        # Line with A record
        if not line.startswith(";;"):
            a_records.append(line)
        # Line with query time
        match = re.search(";; Query time: (?P<query_time>.*) msec", line)
        if match:
            query_time = match.group("query_time").strip()
    return {"a_records": a_records, "query_time_msec": int(query_time)}


@app.route('/bandwidth/<loc>', methods=["GET"])
def bandwidth(loc):
    iperf3_server = get_config()["iperf3_server"]
    duration_bandwidth_test_in_sec = get_config()["duration_bandwidth_test_in_sec"]
    args = ["ip", "netns", "exec", loc, "iperf3", "-c", iperf3_server, "-t", str(duration_bandwidth_test_in_sec), "-J"]
    try:
        output = subprocess.check_output(timeout=duration_bandwidth_test_in_sec + 2, args=args).decode()
    except subprocess.TimeoutExpired:
        raise Exception(f"Timeout occured while executing bandwidth test towards {iperf3_server} (location={loc})")
    except subprocess.CalledProcessError:
        raise Exception(f"Failed to execute bandwidth test towards {iperf3_server} (location={loc})")
    dct = json.loads(output)
    try:
        return {"bandwidth_bits_per_sec": float(dct["end"]["sum_received"]["bits_per_second"])}
    except KeyError:
        raise Exception(f"Failed to extract bandwidth from: {dct}")
