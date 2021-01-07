import json
import logging
import os
import subprocess
from typing import Dict, List, Optional

from nfv_test_api import exceptions, util
from nfv_test_api.config import get_config

LOGGER = logging.getLogger(__name__)


NO_NAMESPACE_VALUE = "none"


def process_namespace(namespace: str, allow_none: Optional[bool] = False) -> Optional[str]:
    """Processes namespace values get by REST handler to check if namespace has been defined (correctly)
    """
    if namespace is None or len(namespace) == 0:
        raise exceptions.ServerError(f"Invalid namespace {namespace}")

    if namespace == NO_NAMESPACE_VALUE:
        if not allow_none:
            raise exceptions.ServerError(f"Invalid namespace {namespace} - this value is a reserved keyword")

        return None

    return namespace


def run_in_ns(namespace: Optional[str], command: List[str]) -> str:
    """ Run the given command in the given namespace and return the result as a string
    """
    command_prefix = ["ip", "netns", "exec", namespace] if namespace else []
    output = subprocess.check_output(command_prefix + command, stderr=subprocess.PIPE)
    return output.decode()


def list_interfaces(namespace: Optional[str] = None) -> List[str]:
    if namespace:
        output = run_in_ns(namespace, ["ip", "-j", "link"])
    else:
        output = subprocess.check_output(["ip", "-j", "link"]).decode()

    interfaces = json.loads(output)
    return [x["ifname"] for x in interfaces]


def list_all_interfaces() -> List[Dict[str, str]]:
    """ List all interface in all namespaces. For each interface the name, namespace and
        mac-address is listed.
    """
    interfaces = []
    for ns in list_net_ns():
        for intf in list_interfaces(ns):
            mac = get_mac(intf, ns)
            if mac is not None:
                interfaces.append(
                    {"namespace": ns, "name": intf, "mac": mac,}
                )

    for intf in list_interfaces():
        mac = get_mac(intf)
        if mac is not None:
            interfaces.append(
                {"namespace": None, "name": intf, "mac": mac,}
            )

    return interfaces


def get_mac(interface: str, namespace: Optional[str] = None) -> Optional[str]:
    if namespace is not None:
        output = run_in_ns(namespace, ["ip", "-j", "link", "show", "dev", interface])
    else:
        output = subprocess.check_output(["ip", "-j", "link", "show", "dev", interface])

    interfaces = json.loads(output)

    if len(interfaces) != 1 or "address" not in interfaces[0]:
        return None

    mac = interfaces[0]["address"]
    if mac == "00:00:00:00:00:00" or mac == "0.0.0.0":
        return None

    return mac


def list_net_ns() -> List[str]:
    try:
        return os.listdir("/var/run/netns")
    except FileNotFoundError:
        return []


def create_namespace(namespace: str) -> None:
    """ Create a new network namespace
    """
    subprocess.check_call(["ip", "netns", "add", namespace])
    run_in_ns(namespace, ["ip", "link", "set", "up", "dev", "lo"])


def delete_namespace(namespace: str) -> None:
    subprocess.check_call(["ip", "netns", "del", namespace])


def ensure_namespace(namespace: str) -> None:
    """ Ensure that the given namespace exists
    """
    if namespace not in list_net_ns():
        create_namespace(namespace)


def move_interface(namespace: str, interface_name: str, new_interface_name: str, old_namespace: Optional[str] = None) -> None:
    """ Move interface_name into namespace and rename it to new_interface_name
    """
    command: List[str] = ["ip", "link", "set", interface_name, "netns", namespace]
    if old_namespace is None:
        subprocess.check_output(command)
    else:
        run_in_ns(old_namespace, command)
    run_in_ns(namespace, ["ip", "link", "set", interface_name, "name", new_interface_name])


def get_interface_state(namespace: str, interface: str) -> Dict:
    """ Get the state of the given interface. This method returns a dict with key "interface".
        The value is a dict with keys:
            up: boolean, true if the service is up
            mtu: integer mtu value
            address: A list of address objects. Each object contains address and family attributes (inet or inet6)
    """
    try:
        output = run_in_ns(namespace, ["ip", "-j", "addr", "ls", "dev", interface])
    except subprocess.CalledProcessError:
        raise exceptions.ServerError(f"Failed to list addresses on interface {interface} (location={namespace})")

    result = [x for x in json.loads(output) if len(x)]

    if len(result) != 1:
        LOGGER.error("Got %s from call", result)
        raise exceptions.ServerError(f"Failed to list addresses on interface {interface} (location={namespace})")

    return {
        "interface": {
            "address": [
                {"address": x["local"], "family": x["family"], "prefixlen": x["prefixlen"]} for x in result[0]["addr_info"]
            ],
            "up": "UP" in result[0]["flags"],
            "mtu": result[0]["mtu"],
        }
    }


def set_interface_state(namespace: str, interface: str, state: Dict) -> None:
    """ Make sure the state of the interface matches the given state
    """
    # verify the link exists and get its current state
    current_state = get_interface_state(namespace, interface)

    # check the up state
    if "up" in state and current_state["interface"]["up"] != state["up"]:
        run_in_ns(namespace, ["ip", "link", "set", "up" if state["up"] else "down", "dev", interface])

    # check the mtu
    if "mtu" in state and current_state["interface"]["mtu"] != state["mtu"]:
        run_in_ns(namespace, ["ip", "link", "set", "mtu", str(state["mtu"]), "dev", interface])

    # check the addresses
    if "address" in state:
        current = set(f"{intf['address']}/{intf['prefixlen']}" for intf in current_state["interface"]["address"])
        desired = set(f"{intf['address']}/{intf['prefixlen']}" for intf in state["address"])
        add = desired - current
        remove = current - desired

        for intf in remove:
            run_in_ns(namespace, ["ip", "address", "delete", intf, "dev", interface])

        for intf in add:
            run_in_ns(namespace, ["ip", "address", "add", intf, "dev", interface])


def create_sub_interface(namespace: str, interface: str, outer_vlan: int, inner_vlan: int = 0) -> None:
    """ Create a dot1q subinterface. Single or double tagged
    """
    run_in_ns(
        namespace,
        ["ip", "link", "add", "name", f"{interface}.{outer_vlan}", "link", interface, "type", "vlan", "id", str(outer_vlan)],
    )
    if inner_vlan > 0:
        run_in_ns(
            namespace,
            [
                "ip",
                "link",
                "add",
                "name",
                f"{interface}.{outer_vlan}.{inner_vlan}",
                "link",
                f"{interface}.{outer_vlan}",
                "type",
                "vlan",
                "id",
                str(inner_vlan),
            ],
        )


def delete_sub_interface(
    namespace: str, interface: str, outer_vlan: int, inner_vlan: int = 0, keep_outer: bool = False
) -> None:
    """ Delete a subinterface
    """
    if inner_vlan > 0:
        full = f"{interface}.{outer_vlan}.{inner_vlan}"
    else:
        full = f"{interface}.{outer_vlan}"

    if full not in list_interfaces(namespace):
        return

    run_in_ns(namespace, ["ip", "link", "delete", "dev", full])
    if inner_vlan > 0 and not keep_outer:
        run_in_ns(namespace, ["ip", "link", "delete", "dev", f"{interface}.{outer_vlan}"])


def setup_namespaces():
    """ Make sure all the namespaces from the config file are created and the correct interfaces are defined
    """
    mac_lookup = {x["mac"]: x for x in util.list_all_interfaces()}
    cfg = get_config()
    for ns in cfg.namespaces.values():
        for intf in ns.interfaces:
            if intf.mac in mac_lookup:
                old_namespace: Optional[str] = mac_lookup[intf.mac]["namespace"]
                new_name: str = mac_lookup[intf.mac]["name"]
                util.ensure_namespace(ns.name)
                util.move_interface(ns.name, new_name, intf.name, old_namespace=old_namespace)
                LOGGER.debug(
                    "Moved interface %s with mac %s to namespace %s and name %s",
                    new_name if old_namespace is None else "%s from %s" % (new_name, old_namespace),
                    intf.mac,
                    ns.name,
                    intf.name,
                )


def list_routes(namespace):
    result = util.run_in_ns(namespace, ["ip", "-j", "route", "ls"])
    routes = json.loads(result)
    for route in routes:
        if route["dst"] == "default":
            route["dst"] = "0.0.0.0/0"
    return routes
