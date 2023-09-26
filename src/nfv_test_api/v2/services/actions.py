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

from pingparsing import PingParsing
from pydantic import ValidationError

from nfv_test_api.host import Host
from nfv_test_api.v2.data.ping import Ping, PingRequest

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
            "-w",
            str(ping_request.timeout),
            "-i",
            str(ping_request.interval),
        ]
        if ping_request.interface is not None:
            command += ["-I", str(ping_request.interface)]

        command += [str(ping_request.destination)]
        stdout, stderr = self.host.exec(command)

        if stderr:
            LOGGER.error("Ping stderr: %s", stderr)
            if not stdout:
                raise RuntimeError(f"Failed to execute ping command: {stderr}")

            LOGGER.warning("%s", stderr)

        ping_result = self.ping_parser.parse(stdout).as_dict()
        try:
            return Ping(**ping_result)  # type: ignore
        except ValidationError as e:
            LOGGER.error("Failed to parse ping response: %s", ping_result)
            LOGGER.error("Ping stdout: %s", stdout)
            raise e
