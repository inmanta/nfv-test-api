import subprocess

import pytest

from nfv_test_api import config
from nfv_test_api.util import create_namespace, get_mac, list_interfaces, list_net_ns, move_interface, run_in_ns


@pytest.fixture(scope="function", autouse=True)
def reset_config():
    config.CONFIG = None


def cleanup_network() -> None:
    """ Cleanup networking by removing tap devices and network namespace
    """
    for namespace in list_net_ns():
        if namespace.startswith("test-"):
            subprocess.check_output(["ip", "netns", "delete", namespace])

    for link in list_interfaces():
        if link.startswith("test"):
            subprocess.check_output(["ip", "link", "delete", link])


def create_test_interface(name: str) -> str:
    """ Create an interface with the given name and return its mac address
    """
    subprocess.check_output(["ip", "tuntap", "add", name, "mode", "tap"])
    return get_mac(name)


@pytest.fixture
def setup_networking():
    """ Create multiple tap devices and a matching configuration file for running tests
    """
    cleanup_network()

    # create network devices
    mac = {}
    for i in range(0, 8):
        mac[f"test{i}"] = create_test_interface(f"test{i}")

    # set mac on test1
    subprocess.check_output(["ip", "link", "set", "address", "fa:16:3e:31:c8:d8", "dev", "test7"])

    # create network namespaces
    for i in range(0, 5):
        create_namespace(f"test-ns-{i}")

    # move interfaces into the namespace
    move_interface("test-ns-1", "test0", "eth0")
    move_interface("test-ns-2", "test1", "eth0")
    move_interface("test-ns-2", "test2", "eth1")
    move_interface("test-ns-3", "test3", "eth0")
    move_interface("test-ns-3", "test4", "eth1")
    move_interface("test-ns-3", "test5", "eth2")
    move_interface("test-ns-4", "test6", "eth0")

    # set an ip on test 6
    run_in_ns("test-ns-4", ["ip", "link", "set", "up", "dev", "eth0"])
    run_in_ns("test-ns-4", ["ip", "address", "add", "192.0.2.1/24", "dev", "eth0"])

    yield

    cleanup_network()


@pytest.fixture
def pre_post_cleanup():
    cleanup_network()
    yield
    cleanup_network()
