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
import time
from ipaddress import IPv4Address

import requests

from nfv_test_api.v2.data.gnodeb import GNodeB, GNodeBCreate, GNodeBStatus
from nfv_test_api.v2.data.ue_5g import UE, UECreate, UEStatus

LOGGER = logging.getLogger(__name__)


def test_create_gnb(nfv_test_api_endpoint: str, nfv_test_api_logs: None) -> None:
    # Create a new gnodeb
    new_gnodeb = GNodeBCreate(
        **{  # type: ignore
            "mcc": "001",
            "mnc": "01",
            "nci": "0x000000010",
            "idLength": 32,
            "tac": 1,
            "linkIp": "127.0.0.1",
            "ngapIp": "127.0.0.1",
            "gtpIp": "127.0.0.1",
            "amfConfigs": [{"address": "127.0.0.1", "port": 38412}],
            "slices": [{"sst": 1, "sd": 1}],
            "ignoreStreamIds": True,
        }
    )
    response = requests.post(
        f"{nfv_test_api_endpoint}/gnodeb", json=new_gnodeb.json_dict()
    )
    LOGGER.debug(response.json())
    response.raise_for_status()

    # Check that the gnobe config is correctly created
    created_gnodeb = GNodeB(**response.json())
    assert created_gnodeb.dict() == new_gnodeb.dict()

    # Get the gnodeb config and check it is consistent with what we created
    response = requests.get(f"{nfv_test_api_endpoint}/gnodeb/0x000000010")
    LOGGER.debug(response.json())
    response.raise_for_status()
    gnodeb = GNodeB(**response.json())
    assert created_gnodeb.dict() == gnodeb.dict()

    # Start the gnodeb
    requests.post(
        f"{nfv_test_api_endpoint}/gnodeb/0x000000010/start"
    ).raise_for_status()

    # Get the status of the gnodeb
    for _ in range(0, 5):
        response = requests.get(f"{nfv_test_api_endpoint}/gnodeb/0x000000010/status")
        LOGGER.debug(response.json())
        if response.status_code == 404:
            # Try again in a second, the gnodeb might not be running yet
            time.sleep(1)
            continue

        response.raise_for_status()
        status = GNodeBStatus(**response.json())
        if not status.terminated:
            continue
        break

    # jenkins runner do not have sctp loaded, the gnodeb should thus be terminated
    assert (
        status.terminated
    ), f"The GnodeB is not terminated, status logs: {str(status.logs)}"

    # Stop the gnodeb
    requests.post(f"{nfv_test_api_endpoint}/gnodeb/0x000000010/stop").raise_for_status()

    # Update the config

    new_gnodeb.gtpIp = IPv4Address("127.0.0.2")
    response = requests.put(
        f"{nfv_test_api_endpoint}/gnodeb/0x000000010", json=new_gnodeb.json_dict()
    )
    LOGGER.debug(response.json())
    response.raise_for_status()

    # verify that the update worked

    response = requests.get(f"{nfv_test_api_endpoint}/gnodeb/0x000000010")
    LOGGER.debug(response.json())
    response.raise_for_status()
    updated_gnodeb = GNodeB(**response.json())
    assert updated_gnodeb.gtpIp == IPv4Address("127.0.0.2")

    # Delete the gnodeb config
    requests.delete(f"{nfv_test_api_endpoint}/gnodeb/0x000000010").raise_for_status()


def test_create_ue(nfv_test_api_endpoint: str, nfv_test_api_logs: None) -> None:
    # Create a new ue
    new_ue = UECreate(
        **{  # type: ignore
            "supi": "imsi-001010000000001",
            "mcc": "001",
            "mnc": "01",
            "key": "465B5CE8B199B49FAA5F0A2EE238A6BC",
            "op": "E8ED289DEBA952E4283B54E88E6183CA",
            "opType": "OP",
            "amf": "8000",
            "imei": "356938035643803",
            "imeiSv": "4370816125816151",
            "gnbSearchList": ["127.0.0.1"],
            "uacAic": {"mps": False, "mcs": False},
            "uacAcc": {
                "normalClass": 0,
                "class11": False,
                "class12": False,
                "class13": False,
                "class14": False,
                "class15": False,
            },
            "sessions": [
                {"type": "IPv4", "apn": "intranet", "slice": {"sst": 1, "sd": 1}}
            ],
            "configured-nssai": [{"sst": 1, "sd": 1}],
            "default-nssai": [{"sst": 1, "sd": 1}],
            "integrity": {"IA1": True, "IA2": True, "IA3": True},
            "ciphering": {"EA1": True, "EA2": True, "EA3": True},
            "integrityMaxRate": {"uplink": "full", "downlink": "full"},
        }
    )
    response = requests.post(f"{nfv_test_api_endpoint}/ue", json=new_ue.json_dict())
    LOGGER.debug(response.json())
    response.raise_for_status()

    # Check that the ue config is correctly created
    created_ue = UE(**response.json())
    assert created_ue.dict() == new_ue.dict()

    # Get the ue config and check it is consistent with what we created
    response = requests.get(f"{nfv_test_api_endpoint}/ue/imsi-001010000000001")
    LOGGER.debug(response.json())
    response.raise_for_status()
    ue = UE(**response.json())
    assert created_ue.dict() == ue.dict()

    # Start the ue
    requests.post(
        f"{nfv_test_api_endpoint}/ue/imsi-001010000000001/start"
    ).raise_for_status()

    # Get the status of the ue
    response = requests.get(f"{nfv_test_api_endpoint}/ue/imsi-001010000000001/status")
    LOGGER.debug(response.json())
    response.raise_for_status()
    status = UEStatus(**response.json())
    assert (
        not status.terminated
    ), f"The UE should not be terminated, status logs: {str(status.logs)}"

    # Stop the ue
    requests.post(
        f"{nfv_test_api_endpoint}/ue/imsi-001010000000001/stop"
    ).raise_for_status()

    # Update the config

    new_ue.gnbSearchList = [IPv4Address("127.0.0.2")]
    response = requests.put(
        f"{nfv_test_api_endpoint}/ue/imsi-001010000000001", json=new_ue.json_dict()
    )
    LOGGER.debug(response.json())
    response.raise_for_status()

    # verify that the update worked

    response = requests.get(f"{nfv_test_api_endpoint}/ue/imsi-001010000000001")
    LOGGER.debug(response.json())
    response.raise_for_status()
    updated_ue = UE(**response.json())
    assert updated_ue.gnbSearchList == [IPv4Address("127.0.0.2")]

    # Delete the ue config
    requests.delete(
        f"{nfv_test_api_endpoint}/ue/imsi-001010000000001"
    ).raise_for_status()
