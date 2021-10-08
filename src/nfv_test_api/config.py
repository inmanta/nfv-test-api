"""
       Copyright 2021 Inmanta

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
import json
from typing import Any, Dict, List, Optional

import yaml


class Interface:
    name: str
    mac: str

    def __init__(self, name: str, mac: str) -> None:
        self.name = name
        self.mac = mac
        self._state = {"address": [], "mtu": 1500, "up": False}

    def get_state(self) -> Dict[str, Any]:
        """State used for simulation mode"""
        return self._state

    def _del_address(self, address) -> None:
        """Add or remove an address from the list"""
        for i, curr in enumerate(self._state["address"]):
            key = f"{curr['address']}/{curr['prefixlen']}"
            if address == key:
                self._state["address"].remove(curr)
                return

    def set_state(self, state) -> None:
        """Set the state, only used for simulation mode"""
        # check the up state
        if "up" in state:
            self._state["up"] = state["up"]

        # check the mtu
        if "mtu" in state:
            self._state["mtu"] = state["mtu"]

        # check the addresses
        if "address" in state:
            current = set(f"{intf['address']}/{intf['prefixlen']}" for intf in self._state["address"])
            desired_map = {f"{intf['address']}/{intf['prefixlen']}": intf for intf in state["address"]}
            desired = set(desired_map.keys())
            add = desired - current
            remove = current - desired

            for intf in remove:
                self._del_address(intf)

            for intf in add:
                self._state["address"].append(desired_map[intf])


class Route:
    dst: str
    gateway: Optional[str]
    interface: Optional[str]

    def __init__(
        self,
        dst: str,
        gateway: Optional[str] = None,
        interface: Optional[str] = None,
    ) -> None:
        self.dst = dst
        if gateway is None and interface is None:
            raise Exception("gateway or interface should be set")
        self.gateway = gateway
        self.interface = interface

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__)


class Namespace:
    name: str
    interfaces: List[Interface]
    routes: List[Route]

    def __init__(self, name: str, interfaces: List[Dict], routes: Optional[List[Dict]] = None) -> None:
        self.name = name
        self.interfaces = []
        self.routes = []
        for intf in interfaces:
            name = intf.get("name")
            mac = intf.get("mac")
            if name is not None and mac is not None:
                self.interfaces.append(Interface(name=name, mac=mac))
        if routes:
            for route in routes:
                subnet = route.get("subnet")
                gateway = route.get("gateway")
                if subnet is not None and gateway is not None:
                    self.routes.append(Route(dst=subnet, gateway=gateway))

    def get_interface(self, name: str) -> Optional[Interface]:
        for intf in self.interfaces:
            if intf.name == name:
                return intf

        return None


class Config:
    namespaces: Dict[str, Namespace]
    host: str
    port: int

    def __init__(self, config: Dict[str, Any]) -> None:
        self._cfg = config
        self.namespaces = {}
        self.host = "127.0.0.1"
        self.port = "8080"

        self._load()

    def _load(self) -> None:
        for ns in self._cfg.get("namespaces", []):
            name = ns.get("name")
            interfaces = ns.get("interfaces")
            if name is None or interfaces is None:
                continue

            self.namespaces[name] = Namespace(name, interfaces)

        server = self._cfg.get("server", {})
        self.host = server.get("host", self.host)
        self.port = server.get("port", self.port)


CONFIG = None


def get_config(config_file: Optional[str] = None, config_dict: Optional[Dict[str, Any]] = None) -> Config:
    global CONFIG
    if CONFIG is not None:
        return CONFIG

    if config_dict is None:
        default_path = "/etc/nfv-test-api.yaml"
        path_config_file = config_file if config_file is not None else default_path
        with open(path_config_file, "r") as stream:
            config_dict = yaml.safe_load(stream)

    CONFIG = Config(config_dict)
    return CONFIG
