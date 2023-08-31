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
from abc import abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic.main import BaseModel

from nfv_test_api.host import Host
from nfv_test_api.v2.data.base_model import IpBaseModel
from nfv_test_api.v2.data.common import CommandStatus

T = TypeVar("T", bound=IpBaseModel)
TC = TypeVar("TC", bound=BaseModel)
TU = TypeVar("TU", bound=BaseModel)
K = TypeVar("K", bound=object)


class BaseService(Generic[T, TC, TU]):
    def __init__(self, host: Host) -> None:
        self.host = host

    @abstractmethod
    def get_all_raw(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_all(self) -> List[T]:
        pass

    @abstractmethod
    def get_one_raw(self, identifier: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_one_or_default(
        self, identifier: str, default: Optional[K] = None
    ) -> Union[T, None, K]:
        pass

    @abstractmethod
    def get_one(self, identifier: str) -> T:
        pass

    @abstractmethod
    def create(self, o: TC) -> T:
        pass

    @abstractmethod
    def update(self, identifier: str, o: TU) -> T:
        pass

    @abstractmethod
    def delete(self, identifier: str) -> None:
        pass

    @abstractmethod
    def status(self) -> CommandStatus:
        pass
