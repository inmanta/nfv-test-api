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
from typing import List, Optional

from pydantic import BaseModel, constr

MacAddress = constr(regex=r"^([0-9A-Fa-f]{2}[:]){5}[0-9A-Fa-f]{2}$")  # type: ignore
Hostname = constr(
    regex=r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$"
)  # type: ignore
SafeName = constr(regex=r"^[0-9A-Z-a-z@#$_\-.]{1,16}$")  # type: ignore


class InputSafeName(BaseModel):
    name: SafeName  # type: ignore  # type: ignore


class InputOptionalSafeName(BaseModel):
    name: Optional[SafeName]  # type: ignore


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


class CommandStatus(BaseModel):
    command: List[str]
    stdout: str
    stderr: str
