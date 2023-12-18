from nfv_test_api.v2.data.interface import (
    InterfaceCreate,
    InterfaceState,
    InterfaceUpdate,
    LinkInfo,
)
import requests
from ipaddress import IPv4Interface

def test_create_unb(nfv_test_api_endpoint: str, nfv_test_api_logs: None) -> None:
    new_interface = InterfaceCreate(  # type: ignore
        name="eth1",
        type=LinkInfo.Kind.VETH,
        mtu=1500
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

    breakpoint()

    # TODO