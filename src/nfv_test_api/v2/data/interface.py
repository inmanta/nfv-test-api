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

from pydantic import BaseModel
from typing_extensions import Literal

from .base_model import IpBaseModel
from .common import Family, MacAddress, SafeName, Scope


class AddrInfo(IpBaseModel):

    family: Family
    prefix_len: int
    scope: Union[Scope, int]
    label: Optional[SafeName]  # type: ignore
    valid_life_time: int
    preferred_life_time: int
    no_prefix_route: bool = False
    auto_join: bool = False


class Addr4Info(AddrInfo):

    family: Literal[Family.INET]
    local: IPv4Address
    broadcast: Optional[IPv4Address]


class Addr6Info(AddrInfo):

    family: Literal[Family.INET6]
    local: IPv6Address
    broadcast: Optional[IPv6Address]
    no_dad: bool = False
    optimistic: bool = False
    home: bool = False
    mng_tmp_addr: bool = False


class LinkInfo(IpBaseModel):
    class Kind(str, Enum):
        BOND = "bond"
        VETH = "veth"
        BRIDGE = "bridge"
        TUN = "tun"
        VLAN = "vlan"

    info_kind: Kind
    info_data: Optional[dict]

    info_slave_kind: Optional[Kind]
    info_slave_data: Optional[dict]


class InterfaceState(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"
    LOWERLAYERDOWN = "LOWERLAYERDOWN"


class InterfaceCreate(BaseModel):
    name: SafeName  # type: ignore
    parent_dev: Optional[SafeName]  # type: ignore
    mtu: Optional[int]
    address: Optional[Union[IPv4Interface, IPv6Interface]]
    broadcast: Optional[Union[IPv4Address, IPv6Address]]
    type: LinkInfo.Kind = LinkInfo.Kind.VETH
    slave_interfaces: Optional[List[SafeName]]  # type: ignore


class InterfaceUpdate(BaseModel):
    name: Optional[SafeName]  # type: ignore
    state: Optional[Union[Literal[InterfaceState.UP], Literal[InterfaceState.DOWN]]]
    mtu: Optional[int]
    addresses: Optional[List[Union[IPv4Interface, IPv6Interface]]]
    master: Optional[Union[SafeName, Literal["nomaster"]]]  # type: ignore
    netns: Optional[Union[SafeName, int]]  # type: ignore


class Interface(IpBaseModel):

    if_index: int
    link_index: Optional[int]
    if_name: SafeName  # type: ignore
    flags: List[SafeName]  # type: ignore
    mtu: int
    max_mtu: Optional[int]
    min_mtu: Optional[int]
    master: Optional[SafeName]  # type: ignore
    oper_state: InterfaceState
    group: SafeName  # type: ignore
    link_type: SafeName  # type: ignore
    address: Optional[MacAddress]  # type: ignore
    broadcast: Optional[MacAddress]  # type: ignore
    link_netns_id: Optional[int]
    link_info: Optional[LinkInfo]
    addr_info: List[Union[Addr4Info, Addr6Info]]
    alt_names: Optional[List[SafeName]]  # type: ignore
