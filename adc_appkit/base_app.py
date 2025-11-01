"""
Base App class with declarative components, DI and request-scope.
"""

from typing import Dict, List, Optional, TYPE_CHECKING, Any

from adc_appkit.component_manager import ComponentDescriptor, ComponentStrategy, ComponentName
from adc_appkit.di_container import DIContainer
from adc_appkit.request_scope import RequestScope, get_request_scope

if TYPE_CHECKING:
    pass

# Type alias для конфигурации компонентов
ComponentsConfig = Dict[str, Dict[str, Any]]


class BaseApp:
    def __init__(self, *, components_config: ComponentsConfig):
        # Собираем дескрипторы компонентов из класса (с учетом MRO для наследования)
        descriptors: Dict[ComponentName, ComponentDescriptor] = {}
        for cls in reversed(self.__class__.mro()):
            for name, attr in cls.__dict__.items():
                if isinstance(attr, ComponentDescriptor):
                    descriptors[name] = attr

        self._descriptors = descriptors
        
        # Создаем DI контейнер
        self._container = DIContainer(
            app=self,
            components=descriptors,
            config=components_config,
            scope_getter=get_request_scope,
        )

    async def start(self) -> None:
        """
        Запускает приложение и все SINGLETON компоненты в правильном порядке.
        
        Получает топологически отсортированный список SINGLETON компонентов
        и запускает их последовательно. Зависимости запускаются раньше зависимых.
        
        При ошибке во время старта останавливает уже запущенные компоненты.
        """
        # Получаем топологический порядок SINGLETON компонентов
        singleton_order = self._container.get_topological_order(ComponentStrategy.SINGLETON)
        
        try:
            # Запускаем компоненты последовательно в топологическом порядке
            for component_name in singleton_order:
                component = self._container.get_component(component_name)
                
                # Если компонент уже запущен - пропускаем
                if component.started:
                    continue
                
                # Запускаем компонент
                await component.start()
        except Exception as e:
            # При ошибке останавливаем все компоненты
            await self.stop()
            raise RuntimeError(f"App start failed: {e}") from e

    async def stop(self) -> None:
        """
        Останавливает приложение и все SINGLETON компоненты в обратном порядке.
        
        Останавливает компоненты в обратном топологическом порядке:
        зависимые компоненты останавливаются раньше зависимостей.
        """
        # Получаем топологический порядок SINGLETON компонентов
        singleton_order = self._container.get_topological_order(ComponentStrategy.SINGLETON)
        
        # Останавливаем компоненты в обратном порядке (зависимые -> зависимости)
        for component_name in reversed(singleton_order):
            # Получаем компонент
            component = self._container.get_component(component_name)
            
            # Если компонент не запущен - пропускаем
            if not component.started:
                continue
            
            # Останавливаем компонент
            await component.stop()

    async def healthcheck(self) -> Dict[str, bool]:
        """
        Проверяет здоровье приложения и всех запущенных SINGLETON компонентов.
        
        Для каждого запущенного SINGLETON компонента вызывает метод is_alive()
        и возвращает словарь с результатами проверки.
        
        Returns:
            Словарь с именами компонентов и их статусом здоровья (True/False)
        """
        result: Dict[str, bool] = {}
        
        # Проверяем здоровье всех SINGLETON компонентов
        for component_name, info in self._container.components.items():
            if info.strategy != ComponentStrategy.SINGLETON:
                continue
            
            component = self._container.get_component(component_name)
            
            # Если компонент не запущен - возвращаем False
            if not component.started:
                result[component_name] = False
                continue
            
            # Проверяем здоровье компонента через is_alive() (всегда async)
            ok = await component.is_alive()
            result[component_name] = bool(ok)
        
        return result

    def request_scope(self, ctx: dict) -> "RequestScope":
        """
        Создает request scope с указанным контекстом.
        
        При входе в контекст:
        - Создает все REQUEST компоненты с конфигом из ctx
        - Запускает их в топологическом порядке
        
        При выходе из контекста:
        - Останавливает все REQUEST компоненты в обратном порядке
        
        Args:
            ctx: Словарь с контекстом запроса (будет передан в компоненты через kwargs)
        
        Returns:
            RequestScope для использования как async context manager
        
        Пример:
            async with app.request_scope({"request_id": "req-123", "user_id": "user-456"}) as req:
                user_service = req.use("user_service")
        """
        # Создаем и возвращаем RequestScope (логика старта в его __aenter__)
        return RequestScope(self, ctx)



    