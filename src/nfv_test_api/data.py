from enum import Enum
from ipaddress import IPv4Address, IPv4Interface, IPv6Address, IPv6Interface
import json
from typing import Any, Callable, List, Optional, Union

from pydantic import BaseModel, constr
from typing_extensions import Literal

MacAddress = constr(regex=r"^([0-9A-Fa-f]{2}[:]){5}[0-9A-Fa-f]{2}$")
SafeName = constr(regex=r"^[0-9A-Z-a-z@#$_\-.]{1,16}$")


def dense_name(string: str) -> str:
    """
    Convert a name to its contracted form, without any "_" in it
    """
    return "".join(string.split("_"))


class InputSafeName(BaseModel):
    name: SafeName


class CommandStatus(BaseModel):
    command: List[str]
    stdout: str
    stderr: str


class Scope(str, Enum):
    GLOBAL = "global"
    LINK = "link"
    HOST = "host"


class Family(str, Enum):
    INET = "inet"
    INET6 = "inet6"
    BRIDGE = "bridge"
    MPLS = "mpls"
    LINK = "link"


class IpBaseModel(BaseModel):
    class Config:
        underscore_attrs_are_private = True
        alias_generator = dense_name
        allow_population_by_field_name = True

    class CreateForm(BaseModel):
        pass

    class UpdateForm(BaseModel):
        pass

    def json_dict(
        self,
        *,
        include: Union['AbstractSetIntStr', 'MappingIntStrAny'] = None,
        exclude: Union['AbstractSetIntStr', 'MappingIntStrAny'] = None,
        by_alias: bool = False,
        skip_defaults: bool = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        encoder: Optional[Callable[[Any], Any]] = None,
        **dumps_kwargs: Any,
    ) -> dict:
        return json.loads(self.json(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            encoder=encoder,
            **dumps_kwargs,
        ))


class AddrInfo(IpBaseModel):

    family: Family
    prefix_len: int
    scope: Union[Scope, int]
    label: Optional[SafeName]
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

    info_kind: Kind
    info_data: Optional[dict]

    info_slave_kind: Optional[Kind]
    info_slave_data: Optional[dict]


class InterfaceState(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"


class Interface(IpBaseModel):

    class CreateForm(BaseModel):
        name: SafeName
        parent_dev: Optional[SafeName]
        mtu: Optional[int]
        address: Optional[Union[IPv4Interface, IPv6Interface]]
        broadcast: Optional[Union[IPv4Address, IPv6Address]]
        type: LinkInfo.Kind = LinkInfo.Kind.VETH

    class UpdateForm(BaseModel):
        state: InterfaceState = InterfaceState.UP
        mtu: int
        addresses: List[Union[IPv4Interface, IPv6Interface]]
        master: Optional[SafeName]
        netns: Optional[Union[SafeName, int]]

    if_index: int
    link_index: Optional[int]
    if_name: SafeName
    flags: List[SafeName]
    mtu: int
    max_mtu: Optional[int]
    min_mtu: Optional[int]
    master: Optional[SafeName]
    oper_state: InterfaceState
    group: SafeName
    link_type: SafeName
    address: Optional[MacAddress]
    broadcast: Optional[MacAddress]
    link_netns_id: Optional[int]
    link_info: Optional[LinkInfo]
    addr_info: List[Union[Addr4Info, Addr6Info]]
    alt_names: Optional[List[SafeName]]


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


class Namespace(IpBaseModel):
    class CreateForm(BaseModel):
        name: SafeName

    name: Optional[SafeName]
    nsid: int
