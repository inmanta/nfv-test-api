import subprocess
import time

import flask
import pytest
import yaml

from nfv_test_api import main, util


@pytest.fixture
def app() -> flask.Flask:
    main.app.testing = True
    return main.app


def test_server(pre_post_cleanup, app: flask.Flask):
    cfg = util.get_config(
        config_dict=yaml.safe_load(
            """
namespaces:
    - name: test-cloud-west1
      interfaces:
        - name: eth0
          mac: "00:16:3e:1c:3e:4a"
    - name: test-cloud-north
      interfaces:
        - name: eth0
          mac: "00:16:3e:24:9a:3d"
    - name: test-cloud-north-east
      interfaces:
        - name: eth0
          mac: "00:16:3e:68:5f:9c"
        - name: eth1
          mac: "00:16:3e:6f:d6:70"
    - name: test-cust-east1
      interfaces:
        - name: eth0
          mac: "00:16:3e:3a:80:2e"
    - name: test-cust-east2
      interfaces:
        - name: eth0
          mac: "00:16:3e:67:b7:7c"
    - name: test-cust-south1
      interfaces:
        - name: eth0
          mac: "00:16:3e:2c:8a:ec"
        - name: eth1
          mac: "00:16:3e:27:2c:09"
"""
        )
    )
    # create all the tap devices
    i = 0
    for ns in cfg.namespaces.values():
        for intf in ns.interfaces:
            subprocess.check_output(["ip", "tuntap", "add", f"test-{i}", "mode", "tap"])
            subprocess.check_output(["ip", "link", "set", "address", intf.mac, "dev", f"test-{i}"])
            i += 1

    # setup the namespace
    util.setup_namespaces()

    assert (
        len([x for x in util.list_all_interfaces() if x["namespace"] == "test-cust-south1" and x["name"].startswith("eth")])
        == 2
    )

    # run api calls
    with app.test_client() as c:
        response = c.get("/")
        assert response.status == "200 OK"
        assert len(response.json) == 6

        response = c.get("/test-cust-south1/")
        assert response.status == "200 OK"
        assert "eth0" in response.json
        assert "eth1" in response.json

        response = c.get("/test-cust-south1/eth0/state")
        assert response.status == "200 OK"
        assert "interface" in response.json
        assert response.json["interface"]["mtu"] == 1500
        assert not response.json["interface"]["up"]

        response = c.get("/test-cust-south1/eth5/state")
        assert response.status == "404 NOT FOUND"

        response = c.post("/test-cust-south1/eth0.100.500")
        assert response.status == "200 OK"

        response = c.get("/test-cust-south1/eth0.100.500/state")
        assert response.status == "200 OK"

        response = c.post(
            "/test-cust-south1/eth0/state", json={"up": True, "address": [{"address": "192.168.150.1", "prefixlen": 24}]}
        )
        assert response.status == "200 OK"

        response = c.get("/test-cust-south1/eth0/state")
        assert response.status == "200 OK"
        assert response.json["interface"]["address"][0]["address"] == "192.168.150.1"
        assert response.json["interface"]["up"]

        response = c.post("/test-cust-south1/eth0.100.500/state", json={"up": True})
        assert response.status == "200 OK"

        response = c.get("/test-cust-south1/lo/state")
        assert response.status == "200 OK"
        assert response.json["interface"]["up"]

        response = c.post("/test-cust-south1/ping?destination=127.0.0.1")
        assert response.status == "200 OK"
        assert response.json["destination"] == "127.0.0.1"
        assert response.json["packet_loss_count"] == 0

        response = c.post("/test-cust-south1/traceroute?destination=127.0.0.1")
        assert response.status == "200 OK"
        assert response.json["destination_ip"] == "127.0.0.1"
        assert len(response.json["hops"]) == 1

        response = c.delete("/test-cust-south1/eth0.100.500")
        assert response.status == "200 OK"
        response = c.get("/test-cust-south1/")
        assert response.status == "200 OK"
        assert "eth0.100.500" not in response.json
        assert "eth0.100" not in response.json
