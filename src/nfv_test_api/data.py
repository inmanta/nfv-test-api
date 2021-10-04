from enum import Enum
from ipaddress import IPv4Address, IPv4Interface, IPv6Address, IPv6Interface
from typing import List, Optional, Union

from pydantic import BaseModel, constr
from typing_extensions import Literal

MacAddress = constr(regex=r"([0-9A-Fa-f]{2}[:]){5}[0-9A-Fa-f]{2}")


def dense_name(string: str) -> str:
    """
    Convert a name to its contracted form, without any "_" in it
    """
    return "".join(string.split("_"))


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

    class CreateForm:
        pass

    class UpdateForm:
        pass


class AddrInfo(IpBaseModel):

    family: Family
    prefix_len: int
    scope: Union[Scope, int]
    label: Optional[str]
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


class Interface(IpBaseModel):

    class State(str, Enum):
        UP = "UP"
        DOWN = "DOWN"
        UNKNOWN = "UNKNOWN"

    class CreateForm:
        name: str
        state: "Interface.State" = "UP"
        mtu: Optional[int]
        addresses: List[Union[IPv4Interface, IPv6Interface]]

    class Update:
        state: "Interface.State" = "UP"
        mtu: Optional[int]
        addresses: List[Union[IPv4Interface, IPv6Interface]]

    if_index: int
    link_index: Optional[int]
    if_name: str
    flags: List[str]
    mtu: int
    max_mtu: Optional[int]
    min_mtu: Optional[int]
    master: Optional[str]
    oper_state: State
    group: str
    link_type: str
    address: Optional[MacAddress]
    broadcast: Optional[MacAddress]
    link_netns_id: Optional[int]
    link_info: Optional[LinkInfo]
    addr_info: List[Union[Addr4Info, Addr6Info]]
    alt_names: Optional[List[str]]


class Route(IpBaseModel):

    class CreateForm:
        dst: Union[IPv4Interface, IPv6Interface, Literal["default"]]

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
    dev: str
    protocol: Union[Protocol, int, str]
    scope: Union[Scope, int]
    flags: List[str]
    pref_src: Optional[Union[IPv4Address, IPv6Address]]
    metric: Optional[int]


class Namespace(IpBaseModel):

    class CreateForm:
        name: str

    name: str
