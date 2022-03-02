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
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel


class Config(BaseModel):
    host: str = "127.0.0.1"
    port: int = "8080"


CONFIG = None


def get_config(config_file: Optional[str] = None, config_dict: Optional[Dict[str, Any]] = None) -> Config:
    global CONFIG
    if CONFIG is not None:
        return CONFIG

    if config_dict is None:
        default_path = "/etc/nfv-test-api.yaml"
        path_config_file = config_file if config_file is not None else default_path
        with open(path_config_file, "r") as stream:
            config_dict = yaml.safe_load(stream)

    CONFIG = Config(**config_dict)
    return CONFIG
