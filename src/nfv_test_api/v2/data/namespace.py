from typing import Optional

from pydantic import BaseModel

from .base_model import IpBaseModel
from .common import SafeName


class NamespaceCreate(BaseModel):
    name: SafeName
    ns_id: Optional[int]


class NamespaceUpdate(BaseModel):
    name: SafeName
    ns_id: Optional[int]


class Namespace(IpBaseModel):

    name: Optional[SafeName]
    ns_id: int
