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


def test_25_move_interface(nfv_test_api_instance: str) -> None:
    # Create a new interface
    new_interface = InterfaceCreate(
        name="test",
        address=IPv4Interface("255.255.255.1/2"),
    )
    response = requests.post(f"{nfv_test_api_instance}/interfaces", json=new_interface.json_dict())
    response.raise_for_status()

    created_interface = Interface(**response.json())

    # Bring the interface up
    patch_interface = InterfaceUpdate(
        state=InterfaceState.UP,
    )
    response = requests.patch(f"{nfv_test_api_instance}/interfaces/{created_interface.if_name}", json=patch_interface.json_dict())
    response.raise_for_status()

    updated_interface = Interface(**response.json())
    assert updated_interface.oper_state == patch_interface.state

    # Create a new namespace
    new_namespace = NamespaceCreate(
        name="test",
    )
    response = requests.post(f"{nfv_test_api_instance}/namespaces", json=new_namespace.json_dict())
    response.raise_for_status()

    created_namespace = Namespace(**response.json())

    # Move interface in new namespace
    patch_interface = InterfaceUpdate(
        netns=created_namespace.ns_id,
    )
    response = requests.patch(f"{nfv_test_api_instance}/interfaces/{created_interface.if_name}", json=patch_interface.json_dict())
    response.raise_for_status()
