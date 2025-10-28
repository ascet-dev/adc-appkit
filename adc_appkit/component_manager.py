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
    Union,
)

# Type aliases для лучшей читаемости и безопасности типов
ConfigDict = Dict[str, Any]
ComponentName = str
DependencyMap = Dict[str, str]

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
    dependencies: DependencyMap  # param_name -> dependency_name после нормализации
    config: Optional[ConfigDict] = None
    instance: Optional[Component] = None  # singleton instance
    state: ComponentState = ComponentState.REGISTERED
    
    def set_state(self, new_state: ComponentState) -> None:
        """Устанавливает новое состояние с валидацией перехода."""
        # Если состояние не изменилось, ничего не делаем
        if self.state == new_state:
            return
            
        # Валидация переходов состояний
        valid_transitions = {
            ComponentState.REGISTERED: [ComponentState.CONFIGURED, ComponentState.ERROR],
            ComponentState.CONFIGURED: [ComponentState.STARTED, ComponentState.ERROR],
            ComponentState.STARTED: [ComponentState.STOPPED, ComponentState.ERROR],
            ComponentState.STOPPED: [ComponentState.CONFIGURED, ComponentState.ERROR],
            ComponentState.ERROR: [ComponentState.REGISTERED, ComponentState.CONFIGURED, ComponentState.STARTED, ComponentState.STOPPED]
        }
        
        if new_state not in valid_transitions.get(self.state, []):
            raise RuntimeError(
                f"Invalid state transition from {self.state.value} to {new_state.value} "
                f"for component. Valid transitions: {[s.value for s in valid_transitions.get(self.state, [])]}"
            )
        
        self.state = new_state


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
        dependencies: Optional[DependencyMap] = None,
    ):
        self.cls: Type[C] = cls
        self.strategy = strategy
        self.config_key = config_key
        self.dependencies = dependencies or {}  # param_name -> component_name
        self.name: str = ""

    def __set_name__(self, owner, name: str):
        self.name = name

    def __get__(self, instance, owner) -> C:
        if instance is None:
            return self  # доступ через класс
        # получаем компонент через контейнер приложения; IDE тип понимает через cast
        # Получаем текущий scope из ContextVar
        current_scope = instance._current_scope.get()
        
        # Для REQUEST компонентов проверяем, что scope установлен
        if self.strategy == ComponentStrategy.REQUEST and current_scope is None:
            raise RuntimeError(
                f"REQUEST component '{self.name}' can only be accessed within request scope. "
                f"Use 'async with app.request_scope() as req: req.{self.name}'"
            )
        
        comp = instance._container.get_component(self.name, scope_cache=current_scope)
        return cast(C, comp)


def component(
    cls: Type[C],
    *,
    strategy: ComponentStrategy = ComponentStrategy.SINGLETON,
    config_key: str,
    dependencies: Optional[DependencyMap] = None,
) -> ComponentDescriptor[C]:
    """Декоратор для декларативного объявления компонентов."""
    return ComponentDescriptor(
        cls, 
        strategy=strategy, 
        config_key=config_key, 
        dependencies=dependencies
    )
