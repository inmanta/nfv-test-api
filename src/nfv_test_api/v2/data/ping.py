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
from ipaddress import IPv4Address, IPv4Interface, IPv6Address, IPv6Interface
from typing import Optional, Union

from pydantic import BaseModel

from nfv_test_api.v2.data.base_model import IpBaseModel

from .common import Hostname, SafeName


class PingRequest(BaseModel):
    destination: Union[Hostname, IPv4Address, IPv6Address]  # type: ignore
    interface: Optional[Union[SafeName, IPv4Interface, IPv6Interface]]  # type: ignore
    count: int = 4
    interval: float = 0.5
    timeout: int = 8


class Ping(IpBaseModel):
    destination: Union[Hostname, IPv4Address, IPv6Address]  # type: ignore
    packet_duplicate_count: int
    packet_duplicate_rate: Optional[float]
    packet_loss_count: int
    packet_loss_rate: float
    packet_receive: int
    packet_transmit: int
    rtt_avg: Optional[float]
    rtt_max: Optional[float]
    rtt_mdev: Optional[float]
    rtt_min: Optional[float]
