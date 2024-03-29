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
from enum import Enum
from ipaddress import IPv4Address, IPv4Interface, IPv6Address, IPv6Interface
from typing import List, Optional, Union

from pydantic import BaseModel, validator
from typing_extensions import Literal

from .base_model import IpBaseModel
from .common import SafeName, Scope


class InputDestination(BaseModel):
    """
    Input for destinations, the purpose of this class is purely for validation of user input
    """

    dst_addr: Union[IPv4Address, IPv6Address, Literal["default"]]
    dst_prefix_len: Optional[int]

    @validator("dst_prefix_len")
    def default_if_prefix_none(
        cls, v: Optional[int], values: dict, **kwargs: object
    ) -> Optional[int]:
        if "dst_addr" not in values:
            return v

        if v is None and values["dst_addr"] != "default":
            raise ValueError(
                "A prefix length has to be provided for any destination address (except default)"
            )

        if v is not None and values["dst_addr"] == "default":
            raise ValueError("The default destination doesn't take any prefix length")

        return v

    @property
    def destination_name(self) -> str:
        return (
            f"{self.dst_addr}/{self.dst_prefix_len}"
            if self.dst_addr != "default"
            else str(self.dst_addr)
        )


class RouteCreate(IpBaseModel):
    """
    Input for creating a route
    """

    dst: Union[IPv4Interface, IPv6Interface, Literal["default"]]
    gateway: Optional[Union[IPv4Address, IPv6Address]]
    dev: SafeName  # type: ignore


class RouteUpdate(IpBaseModel):
    """
    Input for updating a route
    """

    gateway: Optional[Union[IPv4Address, IPv6Address]]
    dev: SafeName  # type: ignore


class Route(IpBaseModel):
    """
    A route as return by the command `ip route`
    """

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
    dev: SafeName  # type: ignore
    protocol: Union[Protocol, int, SafeName]  # type: ignore
    scope: Union[Scope, int]
    flags: List[SafeName]  # type: ignore
    pref_src: Optional[Union[IPv4Address, IPv6Address]]
    metric: Optional[int]
