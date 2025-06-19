from abc import ABC, abstractmethod
from typing import Self


class Service(ABC):

    @classmethod
    @abstractmethod
    async def create(cls, **kwargs) -> Self:
        pass

    async def stop(self) -> None:
        return
