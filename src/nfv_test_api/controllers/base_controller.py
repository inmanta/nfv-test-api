from typing import Generic, List, Optional, TypeVar
from abc import abstractmethod
from nfv_test_api.host import Host
from nfv_test_api.data import CommandStatus, IpBaseModel


T = TypeVar("T", IpBaseModel)


class BaseController(Generic[T]):
    def __init__(self, host: Host) -> None:
        self.host = host

    @abstractmethod
    def get_all_raw(self) -> List[object]:
        pass

    @abstractmethod
    def get_all(self) -> List[T]:
        pass

    @abstractmethod
    def get(self, identifier: str) -> Optional[T]:
        pass

    @abstractmethod
    def delete(self, identifier: str) -> None:
        pass

    @abstractmethod
    def create(self, o: T.CreateForm) -> T:
        pass

    @abstractmethod
    def update(self, identifier: str, o: T.UpdateForm) -> T:
        pass
    
    @abstractmethod
    def status(self) -> CommandStatus:
        pass
