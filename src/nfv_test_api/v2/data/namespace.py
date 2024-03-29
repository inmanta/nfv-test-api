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
from typing import Optional

from .base_model import IpBaseModel
from .common import SafeName


class NamespaceCreate(IpBaseModel):
    """
    Input for creating a network namespace

    :param ns_id: The optional namespace id, if none is provided, one will be picked in the pool of available ids
    """

    name: SafeName  # type: ignore
    ns_id: Optional[int]


class NamespaceUpdate(IpBaseModel):
    """
    Input for updating a network namespace
    """


class Namespace(IpBaseModel):
    """
    A namespace, as returned by the `ip netns list-id` command
    """

    name: Optional[SafeName]  # type: ignore
    ns_id: int
