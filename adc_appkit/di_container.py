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

    def get_component(self, name: ComponentName, *, _visited: Optional[set] = None) -> Component:
        """Получает экземпляр SINGLETON компонента."""
        if name not in self._components:
            raise ValueError(f"Component {name} not registered")
        info = self._components[name]
        
        # Проверяем, что компонент сконфигурирован
        if info.config is None:
            raise RuntimeError(f"Component '{name}' is not configured")
        
        # Проверяем, что это SINGLETON компонент
        if info.strategy != ComponentStrategy.SINGLETON:
            raise RuntimeError(f"Component '{name}' is not a SINGLETON component")
        
        # Если компонент уже создан, возвращаем его БЕЗ сложной логики
        if name in self._instances:
            return self._instances[name]
        
        # Инициализируем множество посещенных компонентов для защиты от циклических зависимостей
        if _visited is None:
            _visited = set()
        
        # Проверяем на циклические зависимости
        if name in _visited:
            cycle = " -> ".join(list(_visited) + [name])
            raise RuntimeError(f"Circular dependency detected: {cycle}")
        
        # Собираем конфигурацию с зависимостями
        config = {**info.config}
        
        # Добавляем зависимости (зависимости имеют приоритет над конфигурацией)
        for k, v in info.dependencies.items():
            # Добавляем текущий компонент в посещенные
            _visited.add(name)
            try:
                dep_component = self.get_component(v, _visited=_visited)
                
                # Зависимости должны быть уже запущены
                if not dep_component.started:
                    raise RuntimeError(
                        f"SINGLETON component '{name}' depends on '{v}' which is not started. "
                        f"Ensure dependencies are started before dependent components."
                    )
                config[k] = dep_component.obj
            finally:
                # Убираем текущий компонент из посещенных
                _visited.discard(name)

        # Создаем экземпляр компонента
        inst = info.component_type()
        inst.set_config(config)
        self._instances[name] = inst
        return inst
