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


class ENodeB(IpBaseModel, extra=Extra.allow):
    """
    An eNodeB identified by its enb_id.
    """

    enb_id: str # indentifier of the eNodeB
    mcc: str  # Mobile Country Code value
    mnc: str  # Mobile Network Code value (2 or 3 digits)
    mme_addr: str
    gtp_bind_addr: str
    s1c_bind_addr: str
    s1c_bind_port: int
    n_prb: int


class ENodeBCreate(ENodeB):
    """
    Input schema for creating a eNodeB
    """


class ENodeBUpdate(ENodeB):
    """
    Input schema for creating a eNodeB
    """


class ENodeBStatus(BaseModel):
    """
    Response to a status call for a running eNobeB.
    """

    status: dict
    terminated: bool
    pid: int
    logs: list[str]
