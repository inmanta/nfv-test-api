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
import logging
from ipaddress import IPv4Interface

import requests

from nfv_test_api.v2.data.interface import (
    Interface,
    InterfaceCreate,
    InterfaceState,
    InterfaceUpdate,
    LinkInfo,
)
from nfv_test_api.v2.data.namespace import Namespace, NamespaceCreate

LOGGER = logging.getLogger(__name__)


def test_25_move_interface(nfv_test_api_endpoint: str, nfv_test_api_logs: None) -> None:
    # Create a new interface
    new_interface = InterfaceCreate(  # type: ignore
        name="test0",
        type=LinkInfo.Kind.VETH,
        peer="test1",
    )
    response = requests.post(
        f"{nfv_test_api_endpoint}/interfaces", json=new_interface.json_dict()
    )
    LOGGER.debug(response.json())
    response.raise_for_status()

    created_interface = Interface(**response.json())

    # Set the first interface address and bring the interface up
    patch_interface = InterfaceUpdate(  # type: ignore
        addresses=[IPv4Interface("192.168.15.2/24")],
        state=InterfaceState.UP,
    )
    response = requests.patch(
        f"{nfv_test_api_endpoint}/interfaces/test0", json=patch_interface.json_dict()
    )
    LOGGER.debug(response.json())
    response.raise_for_status()

    # Set the second interface address and bring the interface up
    patch_interface = InterfaceUpdate(  # type: ignore
        addresses=[IPv4Interface("192.168.15.3/24")],
        state=InterfaceState.UP,
    )
    response = requests.patch(
        f"{nfv_test_api_endpoint}/interfaces/test1", json=patch_interface.json_dict()
    )
    LOGGER.debug(response.json())
    response.raise_for_status()

    updated_interface = Interface(**response.json())
    assert updated_interface.oper_state == InterfaceState.UP

    # Create a new namespace
    new_namespace = NamespaceCreate(  # type: ignore
        name="test",
    )
    response = requests.post(
        f"{nfv_test_api_endpoint}/namespaces", json=new_namespace.json_dict()
    )
    LOGGER.debug(response.json())
    response.raise_for_status()

    created_namespace = Namespace(**response.json())

    # Move interface in new namespace
    patch_interface = InterfaceUpdate(  # type: ignore
        netns=created_namespace.name,
    )
    response = requests.patch(
        f"{nfv_test_api_endpoint}/interfaces/{created_interface.if_name}",
        json=patch_interface.json_dict(),
    )
    LOGGER.debug(response.json())
    response.raise_for_status()
