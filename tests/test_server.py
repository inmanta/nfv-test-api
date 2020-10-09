import json
import subprocess
import time
from typing import Dict, Optional

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
        response = c.post("/test-cloud-west3/")
        assert response.status == "200 OK"

        response = c.get("/")
        assert response.status == "200 OK"
        assert len(response.json) == 7
        assert "test-cloud-west3" in response.json

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

        response = c.post("/test-cust-east1/eth0.100")
        assert response.status == "200 OK"

        response = c.get("/test-cust-east1/eth0.100/state")
        assert response.status == "200 OK"

        response = c.patch(
            "/test-cust-east1/eth0.100",
            json={"destination_namespace": "test-cloud-west3"},
        )
        assert response.status == "200 OK"

        response = c.get("/test-cust-east1/eth0.100/state")
        assert response.status == "404 NOT FOUND"

        response = c.get("/test-cloud-west3/eth0.100/state")
        assert response.status == "200 OK"

        response = c.delete("/test-cloud-west3/")
        assert response.status == "200 OK"

        response = c.get("/")
        assert response.status == "200 OK"
        assert len(response.json) == 6
        assert "test-cloud-west3" not in response.json

        response = c.delete("/test-cust-east1/")
        assert response.status == "500 INTERNAL SERVER ERROR"

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

        # List routes
        response = c.get("/test-cust-south1/routes")
        assert response.status == "200 OK"
        assert len(response.json) > 0
        nb_routes = len(response.json)
        routes_namespace: str = "test-cust-south1"
        routes_subnet: str = "172.16.64.0/18"
        routes_gateway = response.json[0]["prefsrc"]
        routes_interface: str = "eth1"

        def add_delete_route(
            original_routes_length: int,
            namespace: str,
            subnet: str,
            gateway: Optional[str] = None,
            interface: Optional[str] = None,
        ) -> int:
            data: Dict[str, str] = {"subnet": subnet}
            if gateway is not None:
                data["gateway"] = gateway
            if interface is not None:
                data["interface"] = interface

            response = c.post(
                f"/{namespace}/routes",
                data=json.dumps(data),
                content_type="application/json",
            )
            assert response.status == "200 OK"
            assert len(response.json) == original_routes_length + 1

            response = c.delete(
                f"/{namespace}/routes?%s"
                % "&".join(f"{key}={value}" for key, value in data.items())
            )
            assert response.status == "200 OK"
            assert len(response.json) == original_routes_length

            return len(response.json)

        # make sure the interface is up,
        # otherwise adding routes via that interface will fail
        response = c.post(
            f"/{routes_namespace}/{routes_interface}/state", json={"up": True}
        )
        assert response.status == "200 OK"
        response = c.get(f"/{routes_namespace}/{routes_interface}/state")
        assert response.status == "200 OK"
        assert response.json["interface"]["up"]

        nb_routes = add_delete_route(
            nb_routes, routes_namespace, routes_subnet, gateway=routes_gateway
        )
        nb_routes = add_delete_route(
            nb_routes,
            routes_namespace,
            routes_subnet,
            interface=routes_interface,
        )
        nb_routes = add_delete_route(
            nb_routes,
            routes_namespace,
            routes_subnet,
            gateway=routes_gateway,
            interface=routes_interface,
        )

        response = c.delete("/test-cust-south1/eth0.100.500")
        assert response.status == "200 OK"
        response = c.get("/test-cust-south1/")
        assert response.status == "200 OK"
        assert "eth0.100.500" not in response.json
        assert "eth0.100" not in response.json
