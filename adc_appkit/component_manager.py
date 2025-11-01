"""
Component metadata, descriptor and strategy management.

Модуль для управления компонентами приложения.
Содержит классы и функции для декларативного объявления компонентов,
управления их состоянием и стратегиями жизненного цикла.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Type, TypeVar, Generic, cast

from adc_appkit.components.component import Component

ConfigDict = Dict[str, Any]
ComponentName = str
DependencyMap = Dict[str, str]


class ComponentStrategy(Enum):
    SINGLETON = "singleton"
    REQUEST = "request"


class ComponentState(Enum):
    REGISTERED = "registered"
    CONFIGURED = "configured"
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ComponentInfo:
    component_type: type[Component]
    strategy: ComponentStrategy
    config_key: str
    dependencies: DependencyMap
    config: Optional[ConfigDict] = None
    instance: Optional[Component] = None
    state: ComponentState = ComponentState.REGISTERED

    def set_state(self, new: ComponentState) -> None:
        if self.state == new:
            return

        valid = {
            ComponentState.REGISTERED: [ComponentState.CONFIGURED, ComponentState.ERROR],
            ComponentState.CONFIGURED: [ComponentState.STARTED, ComponentState.ERROR],
            ComponentState.STARTED: [ComponentState.STOPPED, ComponentState.ERROR],
            ComponentState.STOPPED: [ComponentState.CONFIGURED, ComponentState.ERROR],
            ComponentState.ERROR: [
                ComponentState.REGISTERED,
                ComponentState.CONFIGURED,
                ComponentState.STARTED,
                ComponentState.STOPPED,
            ],
        }

        if new not in valid.get(self.state, []):
            raise RuntimeError(f"Invalid state {self.state} -> {new}")
        self.state = new


C = TypeVar("C", bound=Component)


class ComponentDescriptor(Generic[C]):
    """Declarative component descriptor with type safety."""

    def __init__(
        self,
        cls: type[C],
        *,
        strategy: ComponentStrategy = ComponentStrategy.SINGLETON,
        config_key: str,
        dependencies: Optional[DependencyMap] = None,
    ):
        self.cls: type[C] = cls
        self.strategy = strategy
        self.config_key = config_key
        self.dependencies = dependencies or {}
        self.name: str = ""

    def __set_name__(self, owner, name: str):
        self.name = name

    def __get__(self, instance, owner) -> C:
        if instance is None:
            return self
        # Без скрытого auto-start: просто вернуть компонент из контейнера.
        return cast(C, instance._container.get_component(self.name))


def component(
    cls: type[C],
    *,
    strategy: ComponentStrategy = ComponentStrategy.SINGLETON,
    config_key: str,
    dependencies: Optional[DependencyMap] = None,
) -> ComponentDescriptor[C]:
    return ComponentDescriptor(
        cls,
        strategy=strategy,
        config_key=config_key,
        dependencies=dependencies,
    )
