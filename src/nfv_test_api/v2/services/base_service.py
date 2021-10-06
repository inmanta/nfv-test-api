from abc import abstractmethod
from typing import Generic, List, TypeVar, Union

from pydantic.main import BaseModel

from nfv_test_api.host import Host
from nfv_test_api.v2.data import CommandStatus, IpBaseModel

T = TypeVar("T", bound=IpBaseModel)
B = TypeVar("B", bound=BaseModel)
K = TypeVar("K", bound=object)


class BaseService(Generic[T]):
    def __init__(self, host: Host) -> None:
        self.host = host

    @abstractmethod
    def get_all_raw(self) -> List[object]:
        pass

    @abstractmethod
    def get_all(self) -> List[T]:
        pass

    @abstractmethod
    def get_or_default(self, identifier: str, default: K = None) -> Union[K, T]:
        pass

    @abstractmethod
    def get(self, identifier: str) -> T:
        pass

    @abstractmethod
    def delete(self, identifier: str) -> None:
        pass

    @abstractmethod
    def create(self, o: B) -> T:
        pass

    @abstractmethod
    def update(self, identifier: str, o: B) -> T:
        pass

    @abstractmethod
    def status(self) -> CommandStatus:
        pass
