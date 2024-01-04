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
from nfv_test_api.v2.data.enodeb import ENodeB, ENodeBCreate, ENodeBUpdate
from nfv_test_api.v2.services.base_service import BaseService, K

LOGGER = logging.getLogger(__name__)


class FileType(str, Enum):
    CONFIG = "config"
    LOG = "log"


def get_file_path(identifier: str, type: FileType) -> Path:
    if type == FileType.CONFIG:
        filename = "enb_" + identifier + ".conf"
        path = Path(Config().enb_config_folder) / filename
    elif type == FileType.LOG:
        filename = "enb_" + identifier + ".log"
        path = Path(Config().enb_log_folder) / filename
    else:
        raise RuntimeError(f"Unkown file type {str(type)}")
    return path


class ENodeBServiceHandler:
    def __init__(self) -> None:
        self.processes: Dict[str, subprocess.Popen] = {}

    def add(self, identifier: str) -> None:
        if identifier not in self.processes:
            command = [
                "/srsRAN_4G/build/srsenb/src/srsenb",
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
            raise Conflict(f"an eNodeB with enb_id {identifier} is already running")

    def kill(self, identifier: str) -> None:
        if identifier in self.processes:
            self.processes[identifier].terminate()
            self.processes[identifier].wait()
            del self.processes[identifier]
        else:
            raise NotFound(f"No process running for eNodeB with enb_id {identifier}")


class ENodeBService(BaseService[ENodeB, ENodeBCreate, ENodeBUpdate]):
    def __init__(self, host: Host, process_handler: ENodeBServiceHandler) -> None:
        super().__init__(host)
        self.process_handler = process_handler

    def get_one_raw(
        self, enb_id: Optional[str] = None, filename: Optional[str] = None
    ) -> Any:
        # Get eNodeB config using enb_id or directly the filename
        if not enb_id and not filename:
            raise NotFound(
                "Please specify either enb_id or filename to get the eNodeB config"
            )
        elif enb_id:
            filename = str(get_file_path(enb_id, FileType.CONFIG))

        try:
            config = configparser.ConfigParser(interpolation=None)
            config.read(filename)  # type: ignore
            return dict(config.items("enb"))
        except configparser.NoSectionError:
            if not enb_id:
                # raise exception only if filename specified
                raise NotFound(f"Could not find eNodeB config {filename}")

    def get_all_raw(self) -> List[Dict[str, Any]]:
        enb_folder = pathlib.Path(Config().enb_config_folder)
        config_files = enb_folder.glob("*.conf")
        configs = []

        for filename in config_files:
            configs.append(self.get_one_raw(filename=filename))  # type: ignore

        return pydantic.parse_obj_as(List[Dict[str, Any]], configs)

    def get_all(self) -> List[ENodeB]:
        enodeb_list: List[ENodeB] = []
        for enodeb_json in self.get_all_raw():
            try:
                enodeb = ENodeB(**enodeb_json)
                enodeb.attach_host(self.host)
                enodeb_list.append(enodeb)
            except ValidationError as e:
                LOGGER.error(
                    f"Failed to parse a eNodeB configuration : {enodeb_json}\n"
                    f"{str(e)}"
                )

        return enodeb_list

    def get_one_or_default(
        self, identifier: str, default: Optional[K] = None
    ) -> Union[ENodeB, None, K]:
        raw_enb = self.get_one_raw(enb_id=identifier)
        if raw_enb is None:
            return default

        enb = ENodeB(**raw_enb)
        enb.attach_host(self.host)
        return enb

    def get_one(self, identifier: str) -> ENodeB:
        enb = self.get_one_or_default(identifier)
        if not enb:
            raise NotFound(f"Could not find eNodeB with enb_id {identifier}")

        return enb

    def create(self, o: ENodeBCreate) -> ENodeB:
        existing_enb = self.get_one_or_default(o.enb_id)
        if existing_enb:
            raise Conflict("An eNodeB config with this enb_id already exists")

        return self.put(o)

    def put(self, o: ENodeBCreate) -> ENodeB:
        """
        Create or update a ENodeB.
        We read the template and set all the fields in config file of the enb.
        """
        template = "/etc/srsran/enb_template.conf"
        filename = get_file_path(o.enb_id, FileType.CONFIG)
        config = configparser.ConfigParser(interpolation=None)
        config.read(template)

        if not config.has_section("enb"):
            config.add_section("enb")
        config.set("enb", "enb_id", o.enb_id)
        config.set("enb", "mcc", o.mcc)
        config.set("enb", "mnc", o.mnc)
        config.set("enb", "mme_addr", str(o.mme_addr))
        config.set("enb", "gtp_bind_addr", str(o.gtp_bind_addr))
        config.set("enb", "s1c_bind_addr", str(o.s1c_bind_addr))
        config.set("enb", "s1c_bind_port", str(o.s1c_bind_port))
        config.set("enb", "n_prb", str(o.n_prb))

        with open(filename, "w+") as fp:
            config.write(fp)

        existing_enb = self.get_one_or_default(o.enb_id)
        if not existing_enb:
            raise RuntimeError(
                "Unexpected error: the created/updated eNodeB config can not be found."
            )

        return existing_enb

    def delete(self, identifier: str) -> None:
        self.get_one(identifier)

        try:
            self.node_status(identifier)
            raise Conflict(f"The eNodeB client {identifier} is still running !")
        except NotFound:
            pass

        try:
            get_file_path(identifier, FileType.CONFIG).unlink()
        except FileNotFoundError:
            raise RuntimeError(
                f"The configuration for eNodeB with enb_id {identifier} doesn't exist"
            )

        existing_enb = self.get_one_or_default(identifier)
        if existing_enb:
            raise RuntimeError(
                "The eNodeB should have been deleted but could not be deleted"
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
            raise NotFound(f"No eNodeB process found for enb_id {identifier}")

        status: Dict[str, Any] = {
            "pid": None,
            "started": False,
            "terminated": False,
        }
        status["pid"] = self.process_handler.processes[identifier].pid

        # Load the logs from the file
        status["logs"] = get_file_path(identifier, FileType.LOG).read_text().split("\n")

        return_code = self.process_handler.processes[identifier].poll()
        if return_code is not None:
            # If the process is still in self.process_handler but has terminated then it is a zombie process
            status["logs"].extend(
                [
                    f"The eNodeB process failed with return code {return_code}.",
                    "The process is still living as zombie process, please call stop to terminate it properly.",
                ]
            )
            status["terminated"] = True

        status["started"] = "==== eNodeB started ===" in status["logs"]

        return status
