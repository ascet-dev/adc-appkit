"""
Модуль базового класса приложения.

Содержит BaseApp класс для создания приложений с декларативными компонентами,
DI контейнером и request scope.
"""

import inspect
from typing import Any, Dict, List, Optional
from contextvars import ContextVar

from adc_appkit.components.component import Component
from adc_appkit.component_manager import ComponentDescriptor, ComponentStrategy, ComponentState
from adc_appkit.di_container import DIContainer


# глобальный contextvar для текущего request scope
_current_scope_var: ContextVar[Optional[Dict[str, Component]]] = ContextVar("_current_scope", default=None)


class BaseApp:
    """Базовый класс приложения с декларативными компонентами, DI и request scope."""

    def __init__(self, *, components_config: Dict[str, dict]):
        # собираем все ComponentDescriptor
        self._descriptors: Dict[str, ComponentDescriptor] = {
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
        self._started_singletons: List[str] = []

        # текущий scope cache для request-компонентов в этом таске
        self._current_scope: ContextVar[Optional[Dict[str, Component]]] = _current_scope_var

    # ------ публичные удобства ------

    def configure(self, name: str, config: Dict[str, Any]) -> None:
        """Установить конфиг компонента по имени (до start() или между restarts)."""
        self._container.configure(name, config)

    async def start(self) -> None:
        """Запуск singleton-компонентов в порядке зависимостей, инъекция singleton-зависимостей, откат при ошибке."""
        order = self._container.get_dependency_order()
        try:
            for name in order:
                info = self._container._components[name]
                if info.strategy != ComponentStrategy.SINGLETON:
                    # request-компоненты не поднимаем на старте
                    continue

                inst = self._container.get_component(name)
                # проверка конфига
                if inst._config is None:
                    raise RuntimeError(f"Config for component '{name}' is not set")

                # ссылка на app для ленивого доступа к request-компонентам
                inst._app = self

                # инжектим ТОЛЬКО singleton-зависимости (чтобы не плодить request-инстансы на старте)
                for dep_name in info.dependencies:
                    dep_info = self._container._components[dep_name]
                    if dep_info.strategy == ComponentStrategy.SINGLETON:
                        dep_inst = self._container.get_component(dep_name)
                        setattr(inst, dep_name, dep_inst)

                if inspect.iscoroutinefunction(inst.start):
                    await inst.start()

                info.state = ComponentState.STARTED
                info.instance = inst
                self._started_singletons.append(name)
        except Exception as e:
            # откат
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
            info.state = ComponentState.STOPPED
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
            self._token = None
            self._cache: Dict[str, Component] = {}
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
