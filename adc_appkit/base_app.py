"""
Модуль базового класса приложения.

Содержит BaseApp класс для создания приложений с декларативными компонентами,
DI контейнером и request scope.
"""

import inspect
from typing import Any, Dict, List, Optional
from contextvars import ContextVar

from adc_appkit.components.component import Component
from adc_appkit.component_manager import ComponentDescriptor, ComponentStrategy, ComponentState, ComponentInfo, ConfigDict, ComponentName
from adc_appkit.di_container import DIContainer

# Type aliases для лучшей читаемости
ComponentsConfig = Dict[ComponentName, ConfigDict]
ScopeCache = Dict[ComponentName, Component]

# глобальный contextvar для текущего request scope
_current_scope_var: ContextVar[Optional[ScopeCache]] = ContextVar("_current_scope", default=None)


class BaseApp:
    """Базовый класс приложения с декларативными компонентами, DI и request scope."""

    def __init__(self, *, components_config: ComponentsConfig):
        # собираем все ComponentDescriptor
        self._descriptors: Dict[ComponentName, ComponentDescriptor] = {
            name: attr for name, attr in self.__class__.__dict__.items() if isinstance(attr, ComponentDescriptor)
        }
        self._container = DIContainer()
        self._container.register_from_descriptors(self._descriptors)

        # автоматическая конфигурация компонентов из components_config
        for name, component_info in self._container._components.items():
            config_key = component_info.config_key
            if config_key in components_config:
                self._container.configure(name, components_config[config_key])
            else:
                raise ValueError(f"Config key '{config_key}' for component '{name}' not found in components_config")

        # список стартовавших singleton-ов
        self._started_singletons: List[ComponentName] = []

        # текущий scope cache для request-компонентов в этом таске
        self._current_scope: ContextVar[Optional[ScopeCache]] = _current_scope_var

    # ------ публичные удобства ------

    def configure(self, name: ComponentName, config: ConfigDict) -> None:
        """Установить конфиг компонента по имени (до start() или между restarts)."""
        self._container.configure(name, config)

    def check_dependency_is_ready(self, name: ComponentName, component_info: ComponentInfo) -> bool:
        for key, dep_name in component_info.dependencies.items():
            if dep_name not in self._container.components:
                raise ValueError(f"Unknown dependency '{dep_name}' for component '{name}'")

            dep_info = self._container.components[dep_name]

            if dep_info.strategy != component_info.strategy:
                raise RuntimeError(f"Dependency '{dep_name}' for component '{name}' is not singleton")

            if dep_name not in self._started_singletons:
                return False

        return True

    async def start_component(self, name: ComponentName, info: ComponentInfo) -> None:
        if info.state != ComponentState.CONFIGURED:
            raise RuntimeError(f"Component '{name}' is not configured")
        
        try:
            # Для singleton компонентов не передаем scope_cache (он не нужен)
            # Для request компонентов scope_cache не должен использоваться при старте
            inst = self._container.get_component(name, scope_cache=None)
            if inst.config is None:
                raise RuntimeError(f"Config for component '{name}' is not set")
            inst.set_app(self)

            await inst.start()

            info.set_state(ComponentState.STARTED)
            info.instance = inst
            self._started_singletons.append(name)
        except Exception as e:
            info.set_state(ComponentState.ERROR)
            raise RuntimeError(f"Failed to start component '{name}': {e}") from e

    async def _start(self) -> None:
        """Запускает singleton компоненты в порядке зависимостей."""
        singleton_components = [c for c in self._container.components.values() if c.strategy == ComponentStrategy.SINGLETON]
        
        while len(self._started_singletons) < len(singleton_components):
            changes = False
            
            for name, info in self._container.components.items():
                if info.strategy != ComponentStrategy.SINGLETON:
                    continue
                if info.state == ComponentState.STARTED:
                    continue
                if not self.check_dependency_is_ready(name, info):
                    continue
                    
                await self.start_component(name, info)
                changes = True

            if not changes:
                raise RuntimeError('Circular dependency or dependency does not exist')

    async def start(self) -> None:
        """Запуск singleton-компонентов в порядке зависимостей, инъекция singleton-зависимостей, откат при ошибке."""
        try:
            await self._start()
        except Exception as e:
            await self.stop()
            raise RuntimeError(f"Failed to start app: {e}") from e

    async def stop(self) -> None:
        """Остановка singleton-компонентов в обратном порядке."""
        for name in reversed(self._started_singletons):
            info = self._container._components[name]
            inst = info.instance
            if inst and hasattr(inst, "stop"):
                res = inst.stop()
                if inspect.isawaitable(res):
                    await res
            info.set_state(ComponentState.STOPPED)
            info.instance = None
        self._started_singletons.clear()

    async def healthcheck(self) -> Dict[str, bool]:
        """Healthcheck только для поднятых singleton-компонентов."""
        results: Dict[str, bool] = {}
        for name in self._started_singletons:
            info = self._container._components[name]
            inst = info.instance
            ok = True
            if inst and hasattr(inst, "is_alive"):
                res = inst.is_alive()
                ok = await res if inspect.isawaitable(res) else bool(res)
            results[name] = bool(ok)
        return results

    # ------ request scope ------

    class _RequestScopeManager:
        def __init__(self, app: "BaseApp"):
            self.app = app
            self._token: Optional[object] = None
            self._cache: ScopeCache = {}
            self._closed: bool = False

        async def __aenter__(self):
            # устанавливаем кэш в contextvar
            self._token = self.app._current_scope.set(self._cache)
            return self

        async def __aexit__(self, exc_type, exc, tb):
            # закрываем все request-компоненты, у которых есть stop()
            for comp in self._cache.values():
                if hasattr(comp, "stop"):
                    res = comp.stop()
                    if inspect.isawaitable(res):
                        await res
            self._cache.clear()
            self._closed = True
            # возвращаем старое значение contextvar
            if self._token is not None:
                self.app._current_scope.reset(self._token)

        # доступ к компонентам внутри scope как к атрибутам
        def __getattr__(self, name: str) -> Component:
            return self.app._container.get_component(name, scope_cache=self._cache)

    def request_scope(self) -> "_RequestScopeManager":
        """
        Использование:
            async with app.request_scope() as req:
                client = req.http
                ...
        Внутри scope один экземпляр request-компонента на весь scope; по exit() — авто stop().
        """
        return BaseApp._RequestScopeManager(self)
