import typing as t
from abc import ABC, abstractmethod
from logging import getLogger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from adc_appkit.base_app import BaseApp

logger = getLogger(__name__)

T = t.TypeVar('T')

# Type aliases для лучшей читаемости и безопасности типов
ConfigDict = t.Dict[str, t.Any]


class Component(ABC, t.Generic[T]):
    """Базовый класс для всех компонентов приложения."""

    def __init__(self):
        self._config: t.Optional[ConfigDict] = None
        self._obj: t.Optional[T] = None
        self._app: t.Optional["BaseApp"] = None
        self._started = False

    @property
    def config(self) -> t.Optional[ConfigDict]:
        """Конфигурация компонента."""
        return self._config

    def set_config(self, config: ConfigDict) -> None:
        """Устанавливает конфигурацию компонента."""
        self._config = config

    def set_app(self, app: "BaseApp") -> None:
        """Устанавливает ссылку на приложение."""
        self._app = app

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


def create_component(cls: t.Type[T]) -> t.Type[Component[T]]:
    class _WrappedComponent(Component[T]):    
        async def _start(self, **config_kwargs) -> T:
            return cls(**config_kwargs)
        
        async def _stop(self) -> None:
            # Если у объекта есть метод close, вызываем его
            if hasattr(self.obj, 'close') and callable(getattr(self.obj, 'close')):
                import inspect
                if inspect.iscoroutinefunction(self.obj.close):
                    await self.obj.close()
                else:
                    self.obj.close()
        
        async def is_alive(self) -> bool:
            # Если у объекта есть метод is_alive, используем его
            if hasattr(self.obj, 'is_alive') and callable(getattr(self.obj, 'is_alive')):
                import inspect
                if inspect.iscoroutinefunction(self.obj.is_alive):
                    return await self.obj.is_alive()
                else:
                    return self.obj.is_alive()
            
            # Если у объекта есть атрибут closed, проверяем его
            if hasattr(self.obj, 'closed'):
                return not self.obj.closed
            
            # По умолчанию считаем живым
            return True

    _WrappedComponent.__name__ = f"Component[{cls.__name__}]"
    _WrappedComponent.__qualname__ = f"Component[{cls.__name__}]"
    
    return _WrappedComponent
