"""
Модуль для управления request scope.

Содержит RequestScope для изоляции REQUEST компонентов в контексте запроса.
"""

from typing import Dict, List, Optional, TYPE_CHECKING
from contextvars import ContextVar

from adc_appkit.component_manager import ComponentName, ComponentStrategy
from adc_appkit.components.component import Component

if TYPE_CHECKING:
    from adc_appkit.base_app import BaseApp

ScopeCache = Dict[ComponentName, Component]

# request-scope storage (кэш компонентов текущего запроса)
_request_scope_var: ContextVar[Optional[ScopeCache]] = ContextVar("_request_scope", default=None)


class RequestScope:
    """
    Менеджер request-scope (async context manager).
    
    Управляет жизненным циклом REQUEST компонентов:
    - Создает и запускает компоненты при входе в контекст
    - Останавливает компоненты при выходе из контекста
    """

    def __init__(self, app: "BaseApp", ctx: dict):
        self.app = app
        self.ctx = ctx
        self.cache: ScopeCache = {}
        self._token: Optional[object] = None
        self._order: List[str] = []  # порядок запуска для остановки

    async def __aenter__(self):
        # Устанавливаем scope в ContextVar для доступа из DIContainer.get_component
        self._token = _request_scope_var.set(self.cache)
        
        # Получаем топологический порядок всех REQUEST компонентов
        request_order = self.app._container.get_topological_order(ComponentStrategy.REQUEST)
        
        # Создаем все компоненты (без запуска)
        for component_name in request_order:
            info = self.app._container.components[component_name]
            
            # Создаем компонент
            inst = info.component_type()
            inst.set_app(self.app)
            
            # Базовый конфиг из config_key + ctx
            cfg = (info.config.get(info.config_key) or {}).copy()
            inst.set_config(cfg)
            
            self.cache[component_name] = inst
        
        # Запускаем компоненты в топологическом порядке
        # При запуске пересоберем конфиг с .obj зависимостей (они уже будут запущены)
        for component_name in request_order:
            component = self.cache[component_name]
            
            if component.started:
                continue
            
            # Пересобираем конфиг с .obj зависимостей (зависимости уже запущены в топологическом порядке)
            info = self.app._container.components[component_name]
            cfg = self.app._container._build_config_with_dependencies(component_name, info, scope=self.cache)
            component.set_config(cfg)
            
            # Запускаем компонент
            await component.start()
            self._order.append(component_name)
        
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Останавливаем REQUEST-компоненты в обратном порядке создания
        for name in reversed(self._order):
            comp = self.cache.get(name)
            if comp and comp.started:
                await comp.stop()
        
        # Очищаем scope и сбрасываем ContextVar
        self.cache.clear()
        if self._token is not None:
            _request_scope_var.reset(self._token)

    def get(self, name: str) -> Component:
        """Получает REQUEST-компонент из кэша."""
        if name not in self.cache:
            raise RuntimeError(f"REQUEST component '{name}' not found in scope")
        return self.cache[name]

    def use(self, name: str):
        """Упрощённый доступ: вернёт .obj компонента."""
        comp = self.get(name)
        return comp.obj


def get_request_scope() -> Optional[ScopeCache]:
    """Получает текущий request scope из ContextVar."""
    return _request_scope_var.get()

