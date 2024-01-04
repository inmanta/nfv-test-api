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

import logging
import time
from ipaddress import IPv4Address, IPv4Interface

import pytest
import requests

from nfv_test_api.v2.data.enodeb import ENodeB, ENodeBCreate, ENodeBStatus
from nfv_test_api.v2.data.interface import (
    InterfaceCreate,
    InterfaceState,
    InterfaceUpdate,
    LinkInfo,
)
from nfv_test_api.v2.data.ue_4g import UE, UECreate, UEStatus

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def setup_interface(nfv_test_api_endpoint: str) -> None:
    new_interface = InterfaceCreate(  # type: ignore
        name="eth1", type=LinkInfo.Kind.VETH, mtu=1500
    )
    response = requests.post(
        f"{nfv_test_api_endpoint}/interfaces", json=new_interface.json_dict()
    )
    response.raise_for_status()

    patch_interface = InterfaceUpdate(  # type: ignore
        addresses=[IPv4Interface("10.20.20.1")],
        state=InterfaceState.UP,
    )
    response = requests.patch(
        f"{nfv_test_api_endpoint}/interfaces/eth1", json=patch_interface.json_dict()
    )
    response.raise_for_status()


def test_create_enb(
    nfv_test_api_endpoint: str, nfv_test_api_logs: None, setup_interface: None
) -> None:
    # Create a new enodeb
    new_enodeb = ENodeBCreate(
        **{  # type: ignore
            "enb_id": "0x19B",
            "mcc": "001",
            "mnc": "01",
            "mme_addr": "10.255.251.2",
            "gtp_bind_addr": "10.20.20.1",
            "s1c_bind_addr": "10.20.20.1",
            "s1c_bind_port": 0,
            "n_prb": 50,
        }
    )
    response = requests.post(
        f"{nfv_test_api_endpoint}/enodeb", json=new_enodeb.json_dict()
    )
    LOGGER.debug(response.json())
    response.raise_for_status()

    # Check that the eNodeB config is correctly created
    created_enodeb = ENodeB(**response.json())
    assert created_enodeb.dict() == new_enodeb.dict()

    # Get the eNodeB config and check it is consistent with what we created
    response = requests.get(f"{nfv_test_api_endpoint}/enodeb/0x19B")
    LOGGER.debug(response.json())
    response.raise_for_status()
    enodeb = ENodeB(**response.json())
    assert created_enodeb.dict() == enodeb.dict()

    # Start the enodeb
    requests.post(f"{nfv_test_api_endpoint}/enodeb/0x19B/start").raise_for_status()

    # Get the status of the eNodeB
    for _ in range(0, 5):
        response = requests.get(f"{nfv_test_api_endpoint}/enodeb/0x19B/status")
        LOGGER.debug(response.json())
        if response.status_code == 404:
            # Try again in a second, the eNodeB might not be running yet
            time.sleep(1)
            continue

        response.raise_for_status()
        status = ENodeBStatus(**response.json())
        if not status.started and not status.terminated:
            # Try again in a second, the eNodeB might not be running yet
            time.sleep(1)
            continue

        assert not status.terminated, "The eNodeB process is terminated"
        break

    requests.post(f"{nfv_test_api_endpoint}/enodeb/0x19B/stop").raise_for_status()

    # Update the config

    new_enodeb.gtp_bind_addr = IPv4Address("127.0.0.2")
    response = requests.put(
        f"{nfv_test_api_endpoint}/enodeb/0x19B", json=new_enodeb.json_dict()
    )
    LOGGER.debug(response.json())
    response.raise_for_status()

    # verify that the update worked

    response = requests.get(f"{nfv_test_api_endpoint}/enodeb/0x19B")
    LOGGER.debug(response.json())
    response.raise_for_status()
    updated_gnodeb = ENodeB(**response.json())
    assert updated_gnodeb.gtp_bind_addr == IPv4Address("127.0.0.2")

    # Delete the gnodeb config
    requests.delete(f"{nfv_test_api_endpoint}/enodeb/0x19B").raise_for_status()


def test_create_ue(nfv_test_api_endpoint: str, nfv_test_api_logs: None) -> None:
    # Create a new ue
    new_ue = UECreate(
        **{  # type: ignore
            "imei": "356938035643803",
            "imsi": "001010000000001",
            "op": "E8ED289DEBA952E4283B54E88E6183CA",
            "k": "465B5CE8B199B49FAA5F0A2EE238A6BC",
            "mode": "soft",
            "algo": "milenage",
        }
    )
    response = requests.post(f"{nfv_test_api_endpoint}/ue_4g", json=new_ue.json_dict())
    LOGGER.debug(response.json())
    response.raise_for_status()

    # Check that the ue config is correctly created
    created_ue = UE(**response.json())
    assert created_ue.dict() == new_ue.dict()

    # Get the ue config and check it is consistent with what we created
    response = requests.get(f"{nfv_test_api_endpoint}/ue_4g/356938035643803")
    LOGGER.debug(response.json())
    response.raise_for_status()
    ue = UE(**response.json())
    assert created_ue.dict() == ue.dict()

    # Start the ue
    requests.post(
        f"{nfv_test_api_endpoint}/ue_4g/356938035643803/start"
    ).raise_for_status()

    # Get the status of the ue
    response = requests.get(f"{nfv_test_api_endpoint}/ue_4g/356938035643803/status")
    LOGGER.debug(response.json())
    response.raise_for_status()
    status = UEStatus(**response.json())
    assert (
        not status.terminated
    ), f"The UE should not be terminated, status logs: {str(status.logs)}"

    # Stop the ue
    requests.post(
        f"{nfv_test_api_endpoint}/ue_4g/356938035643803/stop"
    ).raise_for_status()

    # Update the config

    new_ue.op = "A8ED289DEBA952E4283B54E88E6183CD"
    response = requests.put(
        f"{nfv_test_api_endpoint}/ue_4g/356938035643803", json=new_ue.json_dict()
    )
    LOGGER.debug(response.json())
    response.raise_for_status()

    # verify that the update worked

    response = requests.get(f"{nfv_test_api_endpoint}/ue_4g/356938035643803")
    LOGGER.debug(response.json())
    response.raise_for_status()
    updated_ue = UE(**response.json())
    assert updated_ue.op == new_ue.op

    # Delete the ue config
    requests.delete(f"{nfv_test_api_endpoint}/ue_4g/356938035643803").raise_for_status()
