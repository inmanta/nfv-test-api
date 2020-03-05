#!/usr/bin/python3

import json
import os
import subprocess


def list_interfaces():
    return os.listdir("/sys/class/net/")


def get_mac(device: str) -> str:
    try:
        with open(os.path.join("/sys/class/net/", device, "address")) as fh:
            return fh.read().strip()
    except Exception:
        return None


def list_net_ns():
    try:
        return os.listdir("/var/run/netns")
    except FileNotFoundError:
        return []


def get_netmap():
    with open("/opt/controltool/netmap") as fh:
        return json.load(fh)


def create_namespaces():
    ignore = {"lo", "eth0"}
    interfaces = [i for i in list_interfaces() if i not in ignore]
    interface_to_mac = {i: get_mac(i) for i in interfaces}

    netmap = get_netmap()
    mac_to_network = {v["mac"]: k for k, v in netmap.items()}
    network_to_ip = {k: v["address"] for k, v in netmap.items()}

    network_to_interface = {mac_to_network[interface_to_mac[i]]: i for i in interfaces}

    existing = list_net_ns()

    for net, intf in network_to_interface.items():
        if net in existing:
            print(f"not creating {net}, as it already exists")
        else:
            print(f"creating {net}")
            subprocess.check_call(["ip", "netns", "add", net])
            subprocess.check_call(["ip", "link", "set", intf, "netns", net])

            ip = network_to_ip[net]

            # quick and dirty, get gateway ip
            parts = ip.split(".")
            parts[-1] = "1"

            gw = ".".join(parts)

            port_script = f"""ip link set {intf} name eth0; ip link set eth0 up; ip address add dev eth0 {ip}/24; ip route add default via {gw}"""

            subprocess.check_call(["ip", "netns", "exec", net, "bash", "-c", port_script])


if __name__ == "__main__":
    create_namespaces()
