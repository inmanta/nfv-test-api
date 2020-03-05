import yaml

from nfv_test_api import config
from nfv_test_api.util import (
    create_sub_interface,
    delete_sub_interface,
    get_interface_state,
    list_all_interfaces,
    list_interfaces,
    set_interface_state,
    setup_namespaces,
)


def test_list_interfaces(setup_networking):
    interfaces = list_interfaces()
    assert "test7" in interfaces

    interfaces = list_interfaces("test-ns-1")
    assert "eth0" in interfaces


def test_interface_get_state(setup_networking):
    result = get_interface_state("test-ns-4", "eth0")

    assert "interface" in result
    assert "up" in result["interface"]
    assert result["interface"]["up"]
    assert "mtu" in result["interface"]
    assert result["interface"]["mtu"] == 1500

    assert len(result["interface"]["address"]) == 1
    assert result["interface"]["address"][0]["address"] == "192.0.2.1"
    assert result["interface"]["address"][0]["family"] == "inet"
    assert result["interface"]["address"][0]["prefixlen"] == 24


def test_interface_set_state(setup_networking):
    result = get_interface_state("test-ns-1", "eth0")
    assert not result["interface"]["up"]

    set_interface_state("test-ns-1", "eth0", {"up": True})
    result = get_interface_state("test-ns-1", "eth0")
    assert result["interface"]["up"]

    set_interface_state("test-ns-1", "eth0", {"mtu": 1600})
    result = get_interface_state("test-ns-1", "eth0")
    assert result["interface"]["mtu"] == 1600

    set_interface_state("test-ns-1", "eth0", {"address": [{"address": "192.0.2.15", "prefixlen": "24"}]})
    result = get_interface_state("test-ns-1", "eth0")
    assert result["interface"]["address"][0]["address"] == "192.0.2.15"

    set_interface_state("test-ns-1", "eth0", {"address": [{"address": "192.0.3.15", "prefixlen": "24"}]})
    result = get_interface_state("test-ns-1", "eth0")
    assert len(result["interface"]["address"]) == 1
    assert result["interface"]["address"][0]["address"] == "192.0.3.15"

    set_interface_state("test-ns-1", "eth0", {"address": []})
    result = get_interface_state("test-ns-1", "eth0")
    assert len(result["interface"]["address"]) == 0


def test_list_all_interfaces(setup_networking):
    interfaces = list_all_interfaces()

    assert len([x for x in interfaces if x["namespace"] == "test-ns-3" and x["name"].startswith("eth")]) == 3


def test_setup_ns(setup_networking):
    config.get_config(
        config_dict=yaml.safe_load(
            """namespaces:
    - name: test-ns-5
      interfaces:
        - name: eth0
          mac: "fa:16:3e:31:c8:d8"
        - name: eth1
          mac: "fa:18:3e:31:c8:44"
"""
        )
    )
    setup_namespaces()


def test_sub_interfaces(setup_networking):
    create_sub_interface("test-ns-1", "eth0", 10)
    ifaces = list_interfaces("test-ns-1")
    assert "eth0.10" in ifaces

    delete_sub_interface("test-ns-1", "eth0", 10)
    ifaces = list_interfaces("test-ns-1")
    assert "eth0.10" not in ifaces

    create_sub_interface("test-ns-1", "eth0", 100, 101)
    ifaces = list_interfaces("test-ns-1")
    assert "eth0.100.101" in ifaces
    assert "eth0.100" in ifaces

    delete_sub_interface("test-ns-1", "eth0", 100, 101)
    ifaces = list_interfaces("test-ns-1")
    assert "eth0.100.101" not in ifaces
    assert "eth0.100" not in ifaces

    create_sub_interface("test-ns-1", "eth0", 200, 101)
    ifaces = list_interfaces("test-ns-1")
    assert "eth0.200.101" in ifaces
    assert "eth0.200" in ifaces

    delete_sub_interface("test-ns-1", "eth0", 200, 101, keep_outer=True)
    ifaces = list_interfaces("test-ns-1")
    assert "eth0.200.101" not in ifaces
    assert "eth0.200" in ifaces
