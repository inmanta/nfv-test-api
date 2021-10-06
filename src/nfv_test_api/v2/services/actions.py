from nfv_test_api.host import Host
from nfv_test_api.v2.data import Ping, PingRequest, interface
from pingparsing import PingParsing
from pydantic import ValidationError
import logging


LOGGER = logging.getLogger(__name__)


class ActionsService:
    def __init__(self, host: Host) -> None:
        self.host = host
        self.ping_parser = PingParsing()

    def ping(self, ping_request: PingRequest) -> Ping:
        command = [
            "ping",
            "-c",
            str(ping_request.count),
            "-i",
            str(ping_request.interval).replace(".", ","),
        ]
        if ping_request.interface is not None:
            command += ["-I", str(ping_request.interface)]

        command += [str(ping_request.destination)]
        stdout, stderr = self.host.exec(command)

        if stderr:
            raise RuntimeError(f"Failed to execute ping command: {stderr}")

        ping_result = self.ping_parser.parse(stdout).as_dict()
        try:
            return Ping(**ping_result)
        except ValidationError as e:
            LOGGER.error(f"Failed to parse ping response: {ping_result}")
            raise e
