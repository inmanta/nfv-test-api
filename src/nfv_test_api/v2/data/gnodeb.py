"""
       Copyright 2023 Inmanta

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
from ipaddress import IPv4Address, IPv6Address
from typing import List, Union

from pydantic import Extra

from .base_model import BaseModel, IpBaseModel
from .common import Nci, Slice


class AmfConfig(BaseModel):
    """
    AMF address information
    """

    address: Union[IPv4Address, IPv6Address]
    port: int


class GNodeB(IpBaseModel, extra=Extra.allow):
    """
    A gNodeB identified by its nci.
    """

    mcc: str  # Mobile Country Code value
    mnc: str  # Mobile Network Code value (2 or 3 digits)

    # NR Cell Identity (36-bit)
    nci: Nci  # type: ignore
    idLength: int  # NR gNB ID length in bits [22...32]
    tac: int  # Tracking Area Code

    # gNB's local IP address for Radio Link Simulation (Usually same with local IP)
    linkIp: Union[IPv4Address, IPv6Address]
    # gNB's local IP address for N2 Interface (Usually same with local IP)
    ngapIp: Union[IPv4Address, IPv6Address]
    # gNB's local IP address for N3 Interface (Usually same with local IP)
    gtpIp: Union[IPv4Address, IPv6Address]

    # List of AMF address information
    amfConfigs: List[AmfConfig]
    # List of supported S-NSSAIs by this gNB
    slices: List[Slice]

    # Indicates whether or not SCTP stream number errors should be ignored.
    ignoreStreamIds: bool


class GNodeBCreate(GNodeB):
    """
    Input schema for creating a gNodeB
    """


class GNodeBUpdate(GNodeB):
    """
    Input schema for creating a gNodeB
    """


class GNodeBStatus(BaseModel):
    """
    Response to a status call for a running gNobeB.
    """

    status: dict
    pid: int
    logs: list[str]
