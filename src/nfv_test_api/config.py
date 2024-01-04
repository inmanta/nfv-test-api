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
import pathlib
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel


class Config(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8080
    gnb_config_folder: str = "gnb_config/"
    gnb_log_folder: str = "gnb_log/"
    ue_5g_config_folder: str = "ue_5g_config/"
    ue_5g_log_folder: str = "ue_5g_log/"
    enb_config_folder: str = "enb_config/"
    enb_log_folder: str = "enb_log/"
    ue_4g_config_folder: str = "ue_4g_config/"
    ue_4g_log_folder: str = "ue_4g_log/"


CONFIG = None


def get_config(
    config_file: Optional[str] = None,
    config_dict: Optional[Dict[str, Any]] = None,
) -> Config:
    global CONFIG
    if CONFIG is not None:
        return CONFIG

    if config_dict is None:
        default_path = "/etc/nfv-test-api.yaml"
        path_config_file = config_file if config_file is not None else default_path
        with open(path_config_file, "r") as stream:
            config_dict = yaml.safe_load(stream)

    CONFIG = Config(**config_dict)

    # create gnb folders
    gnb_config_folder = pathlib.Path(CONFIG.gnb_config_folder)
    gnb_config_folder.mkdir(parents=True, exist_ok=True)

    gnb_log_folder = pathlib.Path(CONFIG.gnb_log_folder)
    gnb_log_folder.mkdir(parents=True, exist_ok=True)

    # create 5g ue folders
    ue_5g_config_folder = pathlib.Path(CONFIG.ue_5g_config_folder)
    ue_5g_config_folder.mkdir(parents=True, exist_ok=True)

    ue_5g_log_folder = pathlib.Path(CONFIG.ue_5g_log_folder)
    ue_5g_log_folder.mkdir(parents=True, exist_ok=True)

    # create enb folders
    enb_config_folder = pathlib.Path(CONFIG.enb_config_folder)
    enb_config_folder.mkdir(parents=True, exist_ok=True)

    enb_log_folder = pathlib.Path(CONFIG.enb_log_folder)
    enb_log_folder.mkdir(parents=True, exist_ok=True)

    # create 5g ue folders
    ue_4g_config_folder = pathlib.Path(CONFIG.ue_4g_config_folder)
    ue_4g_config_folder.mkdir(parents=True, exist_ok=True)

    ue_4g_log_folder = pathlib.Path(CONFIG.ue_4g_log_folder)
    ue_4g_log_folder.mkdir(parents=True, exist_ok=True)

    return CONFIG
