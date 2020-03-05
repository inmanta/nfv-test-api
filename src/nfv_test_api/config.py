from typing import Any, Dict, List, Optional

import yaml


class Interface:
    name: str
    mac: str

    def __init__(self, name: str, mac: str) -> None:
        self.name = name
        self.mac = mac


class Namespace:
    name: str
    interfaces: List[Interface]

    def __init__(self, name: str, interfaces: List[Dict]) -> None:
        self.name = name
        self.interfaces = []
        for intf in interfaces:
            name = intf.get("name")
            mac = intf.get("mac")
            if name is not None and mac is not None:
                self.interfaces.append(Interface(name=name, mac=mac))

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
