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
import json
from typing import Any, Callable, Optional, Union

from pydantic import BaseModel

from nfv_test_api.host import Host


def dense_name(string: str) -> str:
    """
    Convert a name to its contracted form, without any "_" in it
    """
    return "".join(string.split("_"))


class IpBaseModel(BaseModel):
    class Config:
        underscore_attrs_are_private = True
        alias_generator = dense_name
        allow_population_by_field_name = True

    _host: Optional[Host]

    def attach_host(self, host: Host) -> None:
        self._host = host

    @property
    def host(self) -> Host:
        if not self._host:
            raise ValueError("No host has been attached to this resource")

        return self._host

    def json_dict(
        self,
        *,
        include: Union["AbstractSetIntStr", "MappingIntStrAny"] = None,  # type: ignore # noqa: F821
        exclude: Union["AbstractSetIntStr", "MappingIntStrAny"] = None,  # type: ignore # noqa: F821
        by_alias: bool = False,
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        encoder: Optional[Callable[[Any], Any]] = None,
        **dumps_kwargs: Any,
    ) -> dict:
        produced_dict: dict = json.loads(
            self.json(
                include=include,
                exclude=exclude,
                by_alias=by_alias,
                skip_defaults=skip_defaults,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
                encoder=encoder,
                **dumps_kwargs,
            )
        )

        return produced_dict
