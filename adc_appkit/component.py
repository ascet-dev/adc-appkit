import typing as t
from abc import ABC, abstractmethod
from logging import getLogger

logger = getLogger(__name__)


class Component[T](ABC):

    def __init__(self, config: t.Dict[str, t.Any] = None, dependencies: t.Dict[str, 'Component'] = None):
        self.config = config
        self._obj: t.Optional[T] = None
        self.started = False
        self.dependencies = dependencies
        # todo: add workers (for refresh tokens for example)

    @property
    def obj(self) -> T:
        if not self.started:
            raise AttributeError('AppContext is not started.')
        return self._obj

    @t.final
    async def start(self):
        """Запускает установку компонента"""
        init_args = self.config or {}
        dependencies = self.dependencies or {}
        obj = await self._start(**init_args, **{k: v.obj for k, v in dependencies.items()})
        self._obj = obj
        self.started = True
        logger.debug('%s client is set', self.__class__.__name__)

    @abstractmethod
    async def _start(self, **kwargs) -> T:
        """Будет выполнен при старте приложения"""
        pass

    @abstractmethod
    async def _stop(self):
        """Будет выполнен при завершении приложения"""

    async def stop(self):
        logger.debug('%s client is stopped', self.__class__.__name__)
        await self._stop()

    @property
    async def is_alive(self) -> bool:
        """Проверяет жив ли компонент"""
        return True

    async def __aenter__(self):
        await self.start()
        return self.obj

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
