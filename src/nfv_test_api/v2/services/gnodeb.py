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
import yaml
import pathlib
from typing import Any, Dict, List, Optional, Set, Union
import subprocess

import pydantic
from pydantic import ValidationError
from werkzeug.exceptions import Conflict, NotFound, ServiceUnavailable  # type: ignore

from nfv_test_api.host import Host
from nfv_test_api.v2.data.common import CommandStatus
from nfv_test_api.v2.data.gnodeb import (
    GNodeB,
    GNodeBCreate,
    GNodeBUpdate,
)
from nfv_test_api.v2.services.base_service import BaseService, K
from nfv_test_api.config import Config

LOGGER = logging.getLogger(__name__)

class GNodeBServiceHandler:
    def __init__(self) -> None:
        self.processes: Dict[subprocess.Popen] = {}
    
    def add(self, identifier: str) -> None:
        config_file_path = Config().gnb_config_folder+"gnb_"+identifier+".yml"
        command = [
            "nr-gnb",
            "-c",
            config_file_path
        ]

        out_file_path = Config().gnb_log_folder+"gnb_"+identifier+".log"
        out = open(out_file_path,"w")
        self.processes[identifier] = subprocess.Popen(
            command,
            shell=False,
            universal_newlines=True,
            stdout=out,
            stderr=out,
        )
    
    def kill(self, identifier: str) -> None:
        if identifier in self.processes:
            self.processes[identifier].terminate()
            self.processes[identifier].wait()
            del self.processes[identifier]

class GNodeBService(BaseService[GNodeB, GNodeBCreate, GNodeBUpdate]):
    def __init__(self, host: Host, process_handler: GNodeBServiceHandler) -> None:
        super().__init__(host)
        self.process_handler = process_handler

    def get_one_raw(self, nci: Optional[str] = None, filename: Optional[str] = None) -> Dict:
        # Get gNodeB config using nci or directly the filename
        if not nci and not filename:
            raise NotFound(f"Please specify either nci or filename to get the gNodeB config")
        elif nci:
            filename = Config().gnb_config_folder+"gnb_"+nci+".yml"

        try:
            with open(filename, 'r') as stream:
                try:
                    return yaml.safe_load(stream)
                except yaml.YAMLError as e:
                    raise RuntimeError(f"Failed to load gNodeB config: {filename}\n" f"{str(e)}")
        except FileNotFoundError:
            if not nci:
                # raise exception only if filename specified
                raise NotFound(f"Could not find gNodeB config {filename}")

    def get_all_raw(self) -> List[Dict[str, Any]]:
        gnb_folder = pathlib.Path(Config().gnb_config_folder)
        config_files = gnb_folder.glob("*.yml")
        configs = []

        for filename in config_files:
            configs.append(self.get_one_raw(filename=filename))

        return pydantic.parse_obj_as(List[Dict[str, Any]], configs)
    
    def get_all(self) -> List[GNodeB]:
        gnodeb_list: List[GNodeB] = []
        for gnodeb_json in self.get_all_raw():
            try:
                gnodeb = GNodeB(**gnodeb_json)
                gnodeb.attach_host(self.host)
                gnodeb_list.append(gnodeb)
            except ValidationError as e:
                LOGGER.error(f"Failed to parse a gNodeB configuration : {gnodeb_json}\n" f"{str(e)}")

        return gnodeb_list
    
    def get_one_or_default(
        self, identifier: str, default: Optional[K] = None
    ) -> Union[GNodeB, None, K]:
        raw_gnb = self.get_one_raw(nci=identifier)
        if raw_gnb is None:
            return default

        gnb = GNodeB(**raw_gnb)
        gnb.attach_host(self.host)
        return gnb

    def get_one(self, identifier: str) -> GNodeB:
        gnb = self.get_one_or_default(identifier)
        if not gnb:
            raise NotFound(f"Could not find gNodeB with nci {identifier}")
        
        return gnb

    def create(self, o: GNodeBCreate) -> GNodeB:
        existing_gnb = self.get_one_or_default(o.nci)
        if existing_gnb:
            raise Conflict("A gNodeB config with this nci already exists")

        filename = "gnb_"+o.nci+".yml"

        with open(Config().gnb_config_folder+filename, 'w') as fh:
            yaml.dump(o.json_dict(), fh, sort_keys=False, default_style=None)

        existing_gnb = self.get_one_or_default(o.nci)
        if not existing_gnb:
            raise RuntimeError("The gNodeB config should have been created but can not be found")

        return existing_gnb

    def delete(self, identifier: str) -> None:
        existing_gnb = self.get_one(identifier)

        filename = "gnb_"+identifier+".yml"
        config_file = pathlib.Path(Config().gnb_config_folder+filename)
        try:
            config_file.unlink()
        except FileNotFoundError:
            raise RuntimeError(f"The configuration for gNodeB with nci {identifier} doesn't exist")

        existing_gnb = self.get_one_or_default(identifier)
        if existing_gnb:
            raise RuntimeError("The gNodeB should have been deleted but could not be deleted")

    def start(self, identifier: str) -> None:
        # make sure the config exists
        gnb = self.get_one(identifier)
        self.process_handler.add(identifier)

    def stop(self, identifier: str) -> None:
        # make sure the config exists
        gnb = self.get_one(identifier)
        self.process_handler.kill(identifier)

    def status(self, identifier: str) -> Dict:
        """
        To be able to execute command on a running node, 
        we use nr-cli command with the name generated internally by UERANSIM. 
        
        The pattern is "UERANSIM-gnb-x-y-z" where:
        - x is the mcc
        - y is the mnc
        - z is the gnbId.
        The gnbId is found from the nci and the idLength, for example:
            idLength = 32,
            nci (36 bits)   : 0000 0000 0000 0000 0000 0000 0100 0010 0001
                              ^                                     ^ ^  ^
                              |                  gnbId              | | cellId |  

            // Splitted values are as below
            gnbId (32 bits) : 0000 0000 0000 0000 0000 0000 0100 0010 = 66 = z
            cellId (4 bits) : 0001 = 1

            source: https://github.com/aligungr/UERANSIM/issues/224
        """

        # make sure the config exists
        gnb = self.get_one(identifier)

        node_name = f"UERANSIM-gnb-{int(gnb.mcc)}-{int(gnb.mnc)}-{int(gnb.nci[:-1], 0)}"
        command = [
            "nr-cli",
            node_name,
            "--exec", 
            "status",
        ]

        stdout, stderr = self.host.exec(command)
        if stderr:
            raise NotFound(f"Failed to fetch gNodeB status: {stderr}")
        
        log_filename = Config().gnb_log_folder+"gnb_"+identifier+".log"
        with open(log_filename, 'r') as out:
            stdout += "\n".join(out.readlines())
        
        return stdout

