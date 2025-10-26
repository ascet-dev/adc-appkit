"""
Модуль контейнера зависимостей (Dependency Injection Container).

Содержит класс DIContainer для управления экземплярами компонентов,
разрешения зависимостей и управления их жизненным циклом.
"""

from typing import Any, Dict, List, Optional

from adc_appkit.components.component import Component
from adc_appkit.component_manager import ComponentDescriptor, ComponentInfo, ComponentStrategy


class DIContainer:
    """Контейнер зависимостей с управлением состоянием и запросным кэшем."""

    def __init__(self):
        self._components: Dict[str, ComponentInfo] = {}
        self._instances: Dict[str, Component] = {}
        self._type_to_name: Dict[type, str] = {}

    def register_from_descriptors(self, descriptors: Dict[str, ComponentDescriptor]):
        """Регистрирует компоненты из дескрипторов; собирает граф зависимостей."""
        # сперва регистрируем все имена и типы → чтобы можно было резолвить типовые depends_on
        for name, desc in descriptors.items():
            if name in self._components:
                raise ValueError(f"Duplicate component name: {name}")
            self._type_to_name[desc.cls] = name
            self._components[name] = ComponentInfo(
                component_type=desc.cls,
                strategy=desc.strategy,
                config_key=desc.config_key,
                dependencies=[],  # заполним ниже
            )

        # теперь нормализуем depends_on → в имена
        for name, desc in descriptors.items():
            raw_deps = desc.depends_on or []
            deps: List[str] = []
            for dep in raw_deps:
                if isinstance(dep, str):
                    deps.append(dep)
                elif isinstance(dep, type) and issubclass(dep, Component):
                    if dep not in self._type_to_name:
                        raise ValueError(f"Dependency type {dep.__name__} for '{name}' is not declared as component")
                    deps.append(self._type_to_name[dep])
                elif isinstance(dep, ComponentDescriptor):
                    # Если передали дескриптор, используем его имя
                    deps.append(dep.name)
                else:
                    raise ValueError(f"Unsupported dependency spec '{dep}' in component '{name}'")
            self._components[name].dependencies = deps

    def configure(self, name: str, config: Dict[str, Any]):
        """Настраивает компонент с заданной конфигурацией."""
        if name not in self._components:
            raise ValueError(f"Component {name} not registered")
        info = self._components[name]
        info.config = config
        info.state = ComponentInfo.state.__class__.CONFIGURED

    def get_dependency_order(self) -> List[str]:
        """Топологическая сортировка по зависимостям."""
        visited = set()
        temp = set()
        order: List[str] = []

        def visit(node: str):
            if node in visited:
                return
            if node in temp:
                raise ValueError(f"Circular dependency detected involving '{node}'")
            temp.add(node)
            for dep in self._components[node].dependencies:
                if dep not in self._components:
                    raise ValueError(f"Unknown dependency '{dep}' for component '{node}'")
                visit(dep)
            temp.remove(node)
            visited.add(node)
            order.append(node)

        for n in self._components:
            visit(n)
        return order

    def get_component(self, name: str, *, scope_cache: Optional[Dict[str, Component]] = None) -> Component:
        """Получает экземпляр компонента. Для REQUEST — кэширует в scope_cache (если дан)."""
        if name not in self._components:
            raise ValueError(f"Component {name} not registered")
        info = self._components[name]

        if info.strategy == ComponentStrategy.SINGLETON:
            if name not in self._instances:
                inst = info.component_type()
                if info.config:
                    inst.set_config(info.config)
                self._instances[name] = inst
            return self._instances[name]

        # REQUEST
        if scope_cache is not None:
            # один объект на scope
            if name not in scope_cache:
                inst = info.component_type()
                if info.config:
                    inst.set_config(info.config)
                scope_cache[name] = inst
            return scope_cache[name]
        # вне scope — создаём каждый раз новый объект
        inst = info.component_type()
        if info.config:
            inst.set_config(info.config)
        return inst
