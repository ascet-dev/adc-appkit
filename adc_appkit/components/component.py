import typing as t
from abc import ABC, abstractmethod
from logging import getLogger

logger = getLogger(__name__)

T = t.TypeVar('T')


class Component(ABC, t.Generic[T]):
    """Базовый класс для всех компонентов приложения."""

    def __init__(self):
        self._config: t.Optional[t.Dict[str, t.Any]] = None
        self._obj: t.Optional[T] = None
        self._app: t.Optional[t.Any] = None  # Будет установлен при старте приложения
        self._started = False

    @property
    def config(self) -> t.Optional[t.Dict[str, t.Any]]:
        """Конфигурация компонента."""
        return self._config

    def set_config(self, config: t.Dict[str, t.Any]) -> None:
        """Устанавливает конфигурацию компонента."""
        self._config = config

    @property
    def obj(self) -> T:
        """Возвращает объект компонента после запуска."""
        if not self._started:
            raise AttributeError('Component is not started.')
        return self._obj

    @property
    def started(self) -> bool:
        """Проверяет, запущен ли компонент."""
        return self._started

    async def start(self) -> None:
        """Запускает компонент."""
        if self._started:
            return
        
        if self._config is None:
            raise RuntimeError(f"Config for component '{self.__class__.__name__}' is not set")
        
        self._obj = await self._start(**self._config)
        self._started = True
        logger.debug('%s component started', self.__class__.__name__)

    @abstractmethod
    async def _start(self, **kwargs) -> T:
        """Будет выполнен при старте компонента."""
        pass

    async def stop(self) -> None:
        """Останавливает компонент."""
        if not self._started:
            return
        
        await self._stop()
        self._started = False
        logger.debug('%s component stopped', self.__class__.__name__)

    @abstractmethod
    async def _stop(self) -> None:
        """Будет выполнен при остановке компонента."""
        pass

    async def is_alive(self) -> bool:
        """Проверяет состояние компонента."""
        return True

    async def __aenter__(self):
        await self.start()
        return self.obj

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
