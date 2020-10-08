import json
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

    # run api calls
    with app.test_client() as c:
        response = c.get("/")
        assert response.status == "200 OK"
        assert not response.json

        app.simulate = True

        response = c.get("/")
        assert response.status == "200 OK"
        assert len(response.json) == 6

        response = c.post("/test-cloud-west3/")
        assert response.status == "200 OK"

        response = c.get("/")
        assert response.status == "200 OK"
        assert len(response.json) == 7
        assert "test-cloud-west3" in response.json

        response = c.post("/test-cloud-west3/")
        assert response.status == "200 OK"

        response = c.get("/test-cloud-north-east/")
        assert response.status == "200 OK"
        assert len(response.json) == 2

        response = c.post("/test-cust-south1/eth0.100.500")
        assert response.status == "200 OK"

        response = c.get("/test-cust-south1/")
        assert response.status == "200 OK"
        assert len(response.json) == 3
        assert "eth0.100.500" in response.json

        response = c.delete("/test-cust-south1/eth0.100.500")
        assert response.status == "200 OK"

        response = c.post("/test-cust-east1/eth0.100")
        assert response.status == "200 OK"

        response = c.get("/test-cust-east1/eth0.100/state")
        assert response.status == "200 OK"

        response = c.patch(
            "/test-cust-east1/eth0.100",
            json={"destination_namespace": "test-cloud-west3"},
        )
        assert response.status == "200 OK"

        response = c.delete("/test-cloud-west3")
        assert response.status == "200 OK"

        response = c.get("/")
        assert response.status == "200 OK"
        assert len(response.json) == 6
        assert "test-cloud-west3" not in response.json

        response = c.delete("/test-cust-east1")
        assert response.status == "500 INTERNAL ERROR"

        response = c.get("/test-cust-east1/eth0.100/state")
        assert response.status == "404 NOT FOUND"

        response = c.get("/test-cust-south1/")
        assert response.status == "200 OK"
        assert len(response.json) == 2
        assert "eth0.100.500" not in response.json

        response = c.get("/test-cust-south1/eth0/state")
        assert response.status == "200 OK"
        assert "interface" in response.json
        assert response.json["interface"]["mtu"] == 1500
        assert not response.json["interface"]["up"]

        response = c.post(
            "/test-cust-south1/eth0/state", json={"address": [{"address": "192.168.150.1", "prefixlen": 24}]}
        )
        assert response.status == "200 OK"
        assert response.json["interface"]["address"] == [{"address": "192.168.150.1", "prefixlen": 24}]

        response = c.post(
            "/test-cust-south1/eth0/state",
            json={"address": [{"address": "192.168.150.1", "prefixlen": 24}, {"address": "192.168.151.1", "prefixlen": 28}]}
        )
        assert response.status == "200 OK"
        assert len(response.json["interface"]["address"]) == 2

        response = c.post(
            "/test-cust-south1/eth0/state",
            json={"address": [{"address": "192.168.151.1", "prefixlen": 28}]}
        )
        assert response.status == "200 OK"
        assert response.json["interface"]["address"] == [{"address": "192.168.151.1", "prefixlen": 28}]

        response = c.post("/test-cust-south1/ping?destination=1.1.1.1")
        assert response.status == "200 OK"
        assert response.json["destination"] == "1.1.1.1"
        assert response.json["packet_loss_count"] == 0

        response = c.post("/test-cust-south1/ping?destination=8.8.8.8")
        assert response.status == "200 OK"
        assert not response.json

        response = c.post("/test-cust-south1/routes", data=json.dumps(dict(subnet="172.16.64.0/18", gateway="192.168.150.1")),
                          content_type='application/json')
        assert response.status == "200 OK"
        assert len(response.json) == 1

        response = c.get("/test-cust-south1/routes")
        assert response.status == "200 OK"
        assert len(response.json) > 0

        response = c.delete("/test-cust-south1/routes?subnet=172.16.64.0/18&gateway=192.168.150.1")
        assert response.status == "200 OK"
        assert len(response.json) == 0

        response = c.post("/test-cloud-west3/")
        assert response.status == "200 OK"
        assert not response.json
        response = c.get("/")
        assert response.status == "200 OK"
        assert len(response.json) == 7
