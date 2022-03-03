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
from ipaddress import IPv4Interface
import logging

import requests

from nfv_test_api.v2.data.interface import Addr4Info, Interface, InterfaceCreate, InterfaceState, InterfaceUpdate
from nfv_test_api.v2.data.namespace import NamespaceCreate, Namespace

LOGGER = logging.getLogger(__name__)


def test_25_move_interface(nfv_test_api_endpoint: str, nfv_test_api_logs: None) -> None:
    # Create a new interface
    new_interface = InterfaceCreate(
        name="test",
    )
    response = requests.post(f"{nfv_test_api_endpoint}/interfaces", json=new_interface.json_dict())
    response.raise_for_status()

    created_interface = Interface(**response.json())

    # Set the interface address and bring the interface up
    patch_interface = InterfaceUpdate(
        addresses=[IPv4Interface("192.168.15.2/24")],
        state=InterfaceState.UP,
    )
    response = requests.patch(f"{nfv_test_api_endpoint}/interfaces/{created_interface.if_name}", json=patch_interface.json_dict())
    response.raise_for_status()

    # Create a new namespace
    new_namespace = NamespaceCreate(
        name="test",
    )
    response = requests.post(f"{nfv_test_api_endpoint}/namespaces", json=new_namespace.json_dict())
    response.raise_for_status()

    created_namespace = Namespace(**response.json())

    # Move interface in new namespace
    patch_interface = InterfaceUpdate(
        netns=created_namespace.ns_id,
    )
    response = requests.patch(f"{nfv_test_api_endpoint}/interfaces/{created_interface.if_name}", json=patch_interface.json_dict())
    response.raise_for_status()
