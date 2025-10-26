"""
Модуль для управления компонентами приложения.

Содержит классы и функции для декларативного объявления компонентов,
управления их состоянием и стратегиями жизненного цикла.
"""

import inspect
from enum import Enum
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Generic,
    cast,
)

from adc_appkit.components.component import Component


# ======================= стратегии и состояния =======================


class ComponentStrategy(Enum):
    SINGLETON = "singleton"  # создаётся один раз на app.start(), закрывается на app.stop()
    REQUEST = "request"  # создаётся на обращение, кэшируется в request_scope, закрывается на выходе из scope


class ComponentState(Enum):
    REGISTERED = "registered"
    CONFIGURED = "configured"
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"


# ======================= метаданные компонента в контейнере =======================


@dataclass
class ComponentInfo:
    component_type: Type[Component]
    strategy: ComponentStrategy
    config_key: str  # ключ для поиска конфигурации в components_config
    dependencies: List[str]  # имена зависимостей после нормализации
    config: Optional[Dict[str, Any]] = None
    instance: Optional[Component] = None  # singleton instance
    state: ComponentState = ComponentState.REGISTERED


# ======================= дескриптор декларативного объявления =======================

C = TypeVar("C", bound=Component)


class ComponentDescriptor(Generic[C]):
    """Дескриптор для декларативного объявления компонентов с IDE-подсказками."""

    def __init__(
        self,
        cls: Type[C],
        *,
        strategy: ComponentStrategy = ComponentStrategy.SINGLETON,
        config_key: str,
        depends_on: List[Any] = None,
    ):
        self.cls: Type[C] = cls
        self.strategy = strategy
        self.config_key = config_key
        self.depends_on = depends_on or []
        self.name: str = ""

    def __set_name__(self, owner, name: str):
        self.name = name

    def __get__(self, instance, owner) -> C:
        if instance is None:
            return self  # доступ через класс
        # получаем компонент через контейнер приложения; IDE тип понимает через cast
        comp = instance._container.get_component(self.name, scope_cache=instance._current_scope.get())
        return cast(C, comp)


def component(
    cls: Type[C],
    *,
    strategy: ComponentStrategy = ComponentStrategy.SINGLETON,
    config_key: str,
    depends_on: List[Any] = None,
) -> ComponentDescriptor[C]:
    """Декоратор для декларативного объявления компонентов."""
    return ComponentDescriptor(cls, strategy=strategy, config_key=config_key, depends_on=depends_on)
