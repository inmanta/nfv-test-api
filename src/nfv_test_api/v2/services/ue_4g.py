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
import configparser
import logging
import pathlib
import subprocess
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pydantic
from pydantic import ValidationError
from werkzeug.exceptions import Conflict, NotFound  # type: ignore

from nfv_test_api.config import Config
from nfv_test_api.host import Host
from nfv_test_api.v2.data.ue_4g import UE, UECreate, UEUpdate
from nfv_test_api.v2.services.base_service import BaseService, K

LOGGER = logging.getLogger(__name__)


class FileType(str, Enum):
    CONFIG = "config"
    LOG = "log"


def get_file_path(identifier: str, type: FileType) -> Path:
    if type == FileType.CONFIG:
        filename = "ue_4g_" + identifier + ".conf"
        path = Path(Config().ue_4g_config_folder) / filename
    elif type == FileType.LOG:
        filename = "ue_4g_" + identifier + ".log"
        path = Path(Config().ue_4g_log_folder) / filename
    else:
        raise RuntimeError(f"Unkown file type {str(type)}")
    return path


class UEServiceHandler:
    def __init__(self) -> None:
        self.processes: Dict[str, subprocess.Popen] = {}

    def add(self, identifier: str) -> None:
        if identifier not in self.processes:
            command = [
                "/srsRAN_4G/build/srsue/src/srsue",
                str(get_file_path(identifier, FileType.CONFIG)),
            ]
            out = get_file_path(identifier, FileType.LOG).open(mode="w+")

            self.processes[identifier] = subprocess.Popen(
                command,
                shell=False,
                universal_newlines=True,
                stdout=out,
                stderr=out,
            )
        else:
            raise Conflict(f"an UE with imei {identifier} is already running")

    def kill(self, identifier: str) -> None:
        if identifier in self.processes:
            self.processes[identifier].terminate()
            self.processes[identifier].wait()
            del self.processes[identifier]
        else:
            raise NotFound(f"No process running for UE with imei {identifier}")


class UEService(BaseService[UE, UECreate, UEUpdate]):
    def __init__(self, host: Host, process_handler: UEServiceHandler) -> None:
        super().__init__(host)
        self.process_handler = process_handler

    def get_one_raw(
        self, imei: Optional[str] = None, filename: Optional[str] = None
    ) -> Any:
        # Get ue config using imei or directly the filename
        if not imei and not filename:
            raise NotFound(
                "Please specify either imei or filename to get the UE config"
            )
        elif imei:
            filename = str(get_file_path(imei, FileType.CONFIG))

        try:
            config = configparser.ConfigParser(interpolation=None)
            config.read(filename)  # type: ignore
            return dict(config.items("usim"))
        except configparser.NoSectionError:
            if not imei:
                # raise exception only if filename specified
                raise NotFound(f"Could not find UE config {filename}")

    def get_all_raw(self) -> List[Dict[str, Any]]:
        ue_folder = pathlib.Path(Config().ue_4g_config_folder)
        config_files = ue_folder.glob("*.conf")
        configs = []

        for filename in config_files:
            configs.append(self.get_one_raw(filename=filename))  # type: ignore

        return pydantic.parse_obj_as(List[Dict[str, Any]], configs)

    def get_all(self) -> List[UE]:
        ue_list: List[UE] = []
        for ue_json in self.get_all_raw():
            try:
                ue = UE(**ue_json)
                ue.attach_host(self.host)
                ue_list.append(ue)
            except ValidationError as e:
                LOGGER.error(
                    f"Failed to parse a UE configuration : {ue_json}\n" f"{str(e)}"
                )

        return ue_list

    def get_one_or_default(
        self, identifier: str, default: Optional[K] = None
    ) -> Union[UE, None, K]:
        raw_ue = self.get_one_raw(imei=identifier)
        if raw_ue is None:
            return default

        ue = UE(**raw_ue)
        ue.attach_host(self.host)
        return ue

    def get_one(self, identifier: str) -> UE:
        ue = self.get_one_or_default(identifier)
        if not ue:
            raise NotFound(f"Could not find UE with imei {identifier}")

        return ue

    def create(self, o: UECreate) -> UE:
        existing_ue = self.get_one_or_default(o.imei)
        if existing_ue:
            raise Conflict("A UE config with this imei already exists")

        return self.put(o)

    def put(self, o: UECreate) -> UE:
        """
        Create or update a UE.
        We read the template and set all the fields in config file of the UE.
        """
        template = "/etc/srsran/ue_template.conf"
        filename = get_file_path(o.imei, FileType.CONFIG)
        config = configparser.ConfigParser(interpolation=None)
        config.read(template)

        if not config.has_section("usim"):
            config.add_section("usim")
        config.set("usim", "imei", o.imei)
        config.set("usim", "imsi", o.imsi)
        config.set("usim", "op", o.op)
        config.set("usim", "k", o.k)
        config.set("usim", "mode", o.mode)
        config.set("usim", "algo", o.algo)

        with open(filename, "w+") as fp:
            config.write(fp)

        existing_ue = self.get_one_or_default(o.imei)
        if not existing_ue:
            raise RuntimeError(
                "Unexpected error: the created/updated UE config can not be found."
            )

        return existing_ue

    def delete(self, identifier: str) -> None:
        self.get_one(identifier)

        try:
            self.node_status(identifier)
            raise Conflict(f"The UE client {identifier} is still running !")
        except NotFound:
            pass

        try:
            get_file_path(identifier, FileType.CONFIG).unlink()
        except FileNotFoundError:
            raise RuntimeError(
                f"The configuration for UE with imei {identifier} doesn't exist"
            )

        existing_ue = self.get_one_or_default(identifier)
        if existing_ue:
            raise RuntimeError(
                "The ue should have been deleted but could not be deleted"
            )

    def start(self, identifier: str) -> None:
        # make sure the config exists
        self.get_one(identifier)
        self.process_handler.add(identifier)

    def stop(self, identifier: str) -> None:
        # make sure the config exists
        self.get_one(identifier)
        self.process_handler.kill(identifier)

    def node_status(self, identifier: str) -> Dict[str, Any]:
        # make sure the config exists
        self.get_one(identifier)

        if identifier not in self.process_handler.processes:
            raise NotFound(f"No 4G user equipment process found for imei {identifier}")

        status: Dict[str, Any] = {"pid": None, "terminated": False}
        status["pid"] = self.process_handler.processes[identifier].pid

        # Load the logs from the file
        with get_file_path(identifier, FileType.LOG).open(mode="r") as out:
            status["logs"] = [line.rstrip("\n") for line in out]

        return_code = self.process_handler.processes[identifier].poll()
        if return_code is not None:
            # If the process is still in self.process_handler but has terminated then it is a zombie process
            status["logs"].extend(
                [
                    f"The 4G user equipment process failed with return code {return_code}.",
                    "The process is still living as zombie process, please call stop to terminate it properly.",
                ]
            )
            status["terminated"] = True

        return status
