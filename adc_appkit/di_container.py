"""
Модуль контейнера зависимостей (Dependency Injection Container).

Содержит класс DIContainer для управления экземплярами компонентов,
разрешения зависимостей и управления их жизненным циклом.
"""

from typing import Any, Dict, List, Optional

from adc_appkit.components.component import Component
from adc_appkit.component_manager import ComponentDescriptor, ComponentInfo, ComponentState, ComponentStrategy, ConfigDict, ComponentName


class DIContainer:
    """Контейнер зависимостей с управлением состоянием и запросным кэшем."""

    def __init__(self):
        self._components: Dict[ComponentName, ComponentInfo] = {}
        self._instances: Dict[ComponentName, Component] = {}
        self._type_to_name: Dict[type, ComponentName] = {}

    @property
    def components(self) -> Dict[ComponentName, ComponentInfo]:
        return self._components

    def register_from_descriptors(self, descriptors: Dict[ComponentName, ComponentDescriptor]):
        """Регистрирует компоненты из дескрипторов; собирает граф зависимостей."""
        # Регистрируем все компоненты
        for name, desc in descriptors.items():
            if name in self._components:
                raise ValueError(f"Duplicate component name: {name}")
            self._type_to_name[desc.cls] = name
            self._components[name] = ComponentInfo(
                component_type=desc.cls,
                strategy=desc.strategy,
                config_key=desc.config_key,
                dependencies=desc.dependencies or {},
            )

    def configure(self, name: ComponentName, config: ConfigDict):
        """Настраивает компонент с заданной конфигурацией."""
        if name not in self._components:
            raise ValueError(f"Component {name} not registered")
        info = self._components[name]
        
        try:
            info.config = config
            info.set_state(ComponentState.CONFIGURED)
        except Exception as e:
            info.set_state(ComponentState.ERROR)
            raise RuntimeError(f"Failed to configure component '{name}': {e}") from e

    def get_component(self, name: ComponentName, *, scope_cache: Optional[Dict[ComponentName, Component]] = None) -> Component:
        """Получает экземпляр компонента. Для REQUEST — кэширует в scope_cache (если дан)."""
        if name not in self._components:
            raise ValueError(f"Component {name} not registered")
        info = self._components[name]
        # Собираем конфигурацию с зависимостями
        config = {**info.config}
        
        # Добавляем зависимости
        for k, v in info.dependencies.items():
            dep_component = self.get_component(v, scope_cache=scope_cache)
            # Для SINGLETON компонентов передаем объект, если он запущен
            if dep_component.started:
                config[k] = dep_component.obj
            else:
                # Если зависимость не запущена, передаем сам компонент
                config[k] = dep_component

        if info.strategy == ComponentStrategy.SINGLETON:
            if name not in self._instances:
                inst = info.component_type()
                inst.set_config(config)
                self._instances[name] = inst
            return self._instances[name]

        # REQUEST
        if scope_cache is not None:
            # один объект на scope
            if name not in scope_cache:
                inst = info.component_type()
                inst.set_config(config)
                scope_cache[name] = inst
            return scope_cache[name]
        
        # вне scope — создаём каждый раз новый объект
        inst = info.component_type()
        inst.set_config(config)
        return inst
