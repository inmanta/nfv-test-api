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
from typing import Optional

from pydantic import Extra

from .base_model import BaseModel, IpBaseModel
from .common import Imsi


class UE(IpBaseModel, extra=Extra.allow):
    """
    A UE identified by its imei.
    """

    # Imsi is the 15 digit International Mobile Station Equipment Identity (SIM)
    imsi: Imsi  # type: ignore
    imei: str  # 15 digit International Mobile Subscriber Identity

    op: str  # 128-bit Operator Variant Algorithm Configuration Field (hex)
    k: str  # 128-bit subscriber key (hex)
    mode: Optional[str] = "soft"  # USIM mode (soft/pcsc)
    algo: Optional[str] = "milenage"  # Authentication algorithm (xor/milenage)


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

    terminated: bool
    pid: int
    logs: list[str]
