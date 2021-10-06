from enum import Enum
from ipaddress import IPv4Address, IPv4Interface, IPv6Address, IPv6Interface
from typing import List, Optional, Union

from pydantic import BaseModel, validator
from typing_extensions import Literal

from .base_model import IpBaseModel
from .common import SafeName, Scope


class InputDestination(BaseModel):
    dst_addr: Union[IPv4Address, IPv6Address, Literal["default"]]
    dst_prefix_len: Optional[int]

    @validator("dst_prefix_len")
    def default_if_prefix_none(cls, v: Optional[int], values, **kwargs) -> Optional[int]:
        if "dst_addr" not in values:
            return v

        if v is None and values["dst_addr"] != "default":
            raise ValueError("A prefix length has to be provided for any destination address (except default)")

        if v is not None and values["dst_addr"] == "default":
            raise ValueError("The default destination doesn't take any prefix length")

        return v

    @property
    def destination_name(self) -> str:
        return f"{self.dst_addr}/{self.dst_prefix_len}" if self.dst_addr != "default" else self.dst_addr


class RouteCreate(BaseModel):
    pass


class RouteUpdate(BaseModel):
    pass


class Route(IpBaseModel):
    class Type(str, Enum):
        UNICAST = "unicast"
        LOCAL = "local"
        BROADCAST = "broadcast"
        MULTICAST = "multicast"
        THROW = "throw"
        UNREACHABLE = "unreachable"
        PROHIBIT = "prohibit"
        BLACKHOLE = "blackhole"
        NAT = "nat"

    class Protocol(str, Enum):
        BOOT = "boot"
        STATIC = "static"
        KERNEL = "kernel"
        REDIRECT = "redirect"
        RA = "ra"

    type: Type
    dst: Union[IPv4Interface, IPv6Interface, Literal["default"]]
    gateway: Optional[Union[IPv4Address, IPv6Address]]
    dev: SafeName
    protocol: Union[Protocol, int, SafeName]
    scope: Union[Scope, int]
    flags: List[SafeName]
    pref_src: Optional[Union[IPv4Address, IPv6Address]]
    metric: Optional[int]
