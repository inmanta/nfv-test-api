from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, constr

MacAddress = constr(regex=r"^([0-9A-Fa-f]{2}[:]){5}[0-9A-Fa-f]{2}$")
Hostname = constr(
    regex=r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$"
)
SafeName = constr(regex=r"^[0-9A-Z-a-z@#$_\-.]{1,16}$")


class InputSafeName(BaseModel):
    name: SafeName


class InputOptionalSafeName(BaseModel):
    name: Optional[SafeName]


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
