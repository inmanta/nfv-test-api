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
from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from typing import List, Optional, Union

from pydantic import Extra, Field

from .base_model import BaseModel, IpBaseModel
from .common import Slice, Supi


class OpType(str, Enum):
    OP = "OP"
    OPC = "OPC"


class PDUSessionType(str, Enum):
    IPV4 = "IPv4"


class MaxRate(str, Enum):
    FULL = "full"
    KBPS = "64kbps"


class UacAic(BaseModel):
    """
    UAC Access Identities Configuration
    """

    mps: bool
    mcs: bool


class UacAcc(BaseModel):
    """
    UAC Access Control Class
    """

    normalClass: int
    class11: bool
    class12: bool
    class13: bool
    class14: bool
    class15: bool


class Session(BaseModel):
    """
    Initial PDU session to be established
    """

    type: PDUSessionType
    apn: Optional[str] = None
    slice: Optional[Slice] = None


class Integrity(BaseModel):
    """
    Supported integrity algorithms by this UE
    """

    IA1: bool
    IA2: bool
    IA3: bool


class Ciphering(BaseModel):
    """
    Supported encryption algorithms by this UE
    """

    EA1: bool
    EA2: bool
    EA3: bool


class IntegrityMaxRate(BaseModel):
    """
    Integrity protection maximum data rate for user plane
    """

    uplink: MaxRate
    downlink: MaxRate


class UE(IpBaseModel, extra=Extra.allow):
    """
    A UE identified by its supi.
    """

    # IMSI number of the UE. IMSI = [MCC|MNC|MSISDN] (In total 15 digits)
    supi: Supi  # type: ignore
    mcc: str  # Mobile Country Code value of HPLMN
    mnc: str  # Mobile Network Code value of HPLMN (2 or 3 digits)

    key: str
    op: str
    opType: OpType

    amf: str
    imei: str
    imeiSv: str

    gnbSearchList: List[Union[IPv4Address, IPv6Address]]

    uacAic: UacAic
    uacAcc: UacAcc

    sessions: List[Session]

    configured_nssai: List[Slice] = Field(alias="configured-nssai")
    default_nssai: List[Slice] = Field(alias="default-nssai")

    integrity: Integrity
    ciphering: Ciphering

    integrityMaxRate: IntegrityMaxRate


class UECreate(UE):
    """
    Input schema for creating a UE
    """


class UEUpdate(UE):
    """
    Input schema for creating a UE
    """


class UEStatus(BaseModel):
    """
    Response to a status call for a running UE.
    """

    status: dict
    pid: int
    logs: list[str]
