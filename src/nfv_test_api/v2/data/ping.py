from ipaddress import IPv4Address, IPv4Interface, IPv6Address, IPv6Interface
from typing import Optional, Union

from pydantic import BaseModel

from nfv_test_api.v2.data.base_model import IpBaseModel

from .common import Hostname, SafeName


class PingRequest(BaseModel):
    destination: Union[Hostname, IPv4Address, IPv6Address]
    interface: Optional[Union[SafeName, IPv4Interface, IPv6Interface]]
    count: int = 4
    interval: float = 0.5


class Ping(IpBaseModel):
    destination: Union[Hostname, IPv4Address, IPv6Address]
    packet_duplicate_count: int
    packet_duplicate_rate: float
    packet_loss_count: int
    packet_loss_rate: float
    packet_receive: int
    packet_transmit: int
    rtt_avg: float
    rtt_max: float
    rtt_mdev: float
    rtt_min: float
