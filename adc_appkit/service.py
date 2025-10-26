from abc import ABC, abstractmethod
from typing import TypeVar

T = TypeVar('T', bound='Service')


class Service(ABC):

    @classmethod
    @abstractmethod
    async def create(cls, **kwargs) -> T:
        pass

    async def stop(self) -> None:
        return
