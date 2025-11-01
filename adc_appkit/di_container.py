"""
Dependency Injection Container: creation, configuration, and request-scope assembly with context.

Содержит класс DIContainer для управления экземплярами компонентов,
разрешения зависимостей и управления их жизненным циклом.
"""

from typing import Dict, List, Set, Optional, Callable, TYPE_CHECKING, Any

from adc_appkit.components.component import Component
from adc_appkit.component_manager import (
    ComponentDescriptor,
    ComponentInfo,
    ComponentState,
    ComponentStrategy,
    ComponentName,
    ConfigDict,
)

if TYPE_CHECKING:
    from adc_appkit.base_app import BaseApp

ScopeCache = Dict[ComponentName, Component]


class DIContainer:

    def __init__(
        self, 
        app: "BaseApp", 
        components: Dict[ComponentName, ComponentDescriptor], 
        config: ConfigDict,
        scope_getter: Callable[[], Optional[ScopeCache]] = None,
    ):
        self.app = app
        self._components: Dict[ComponentName, ComponentInfo] = {}
        self._instances: Dict[ComponentName, Component] = {}  # SINGLETON instances
        self._get_scope = scope_getter or (lambda: None)
        self.register(components, config)
        self.validate_dependency_graph()
    
    @property
    def components(self) -> Dict[ComponentName, ComponentInfo]:
        """Публичный доступ к информации о компонентах."""
        return self._components

    def register(self, components: Dict[ComponentName, ComponentDescriptor], config: ConfigDict):
        """Register components in the container."""
        for name, d in components.items():
            if name in self._components:
                raise ValueError(f"Duplicate component name: {name}")
            self._components[name] = ComponentInfo(
                component_type=d.cls,
                strategy=d.strategy,
                config_key=d.config_key,
                dependencies=d.dependencies or {},
                config=config.get(d.config_key, {}),
            )
            self._components[name].set_state(ComponentState.CONFIGURED)

    def _traverse_dependency_graph(
        self,
        start_nodes: Optional[List[ComponentName]] = None,
        strategy_filter: Optional[ComponentStrategy] = None,
        check_cycles: bool = True,
        include_only_strategy_deps: bool = False,
        on_visit: Optional[Callable[[ComponentName, ComponentInfo], None]] = None,
        on_complete: Optional[Callable[[ComponentName, ComponentInfo], None]] = None,
    ) -> List[ComponentName]:
        """
        Универсальный метод для обхода графа зависимостей.
        
        Args:
            start_nodes: Список узлов для начала обхода. Если None - обходятся все компоненты.
            strategy_filter: Фильтр по стратегии. Если None - обходятся все стратегии.
            check_cycles: Проверять ли циклические зависимости.
            include_only_strategy_deps: Обходить только зависимости той же стратегии.
            on_visit: Callback при посещении узла (принимает name, info).
            on_complete: Callback после обхода всех зависимостей (принимает name, info).
        
        Returns:
            Список компонентов в порядке обхода (для топологической сортировки).
        """
        visited: Set[ComponentName] = set()
        result: List[ComponentName] = []
        temp_visited: Set[ComponentName] = set() if check_cycles else None
        cycle_path: List[ComponentName] = [] if check_cycles else None
        
        def dfs(name: ComponentName):
            """Обход графа в глубину."""
            # Проверка циклов (если включена)
            if check_cycles and name in temp_visited:
                idx = cycle_path.index(name)
                cycle = " -> ".join(cycle_path[idx:] + [name])
                raise RuntimeError(f"Circular dependency detected: {cycle}")
            
            # Если компонент уже обработан, пропускаем
            if name in visited:
                return
            
            # Проверка существования компонента
            if name not in self._components:
                raise ValueError(f"Unknown component '{name}'")
            
            info = self._components[name]
            
            # Фильтр по стратегии
            if strategy_filter is not None and info.strategy != strategy_filter:
                return
            
            # Отслеживание пути для обнаружения циклов
            if check_cycles:
                temp_visited.add(name)
                cycle_path.append(name)
            
            # Callback при посещении
            if on_visit:
                on_visit(name, info)
            
            # Обходим зависимости
            for param_name, dep_name in info.dependencies.items():
                # Проверка существования зависимости
                if dep_name not in self._components:
                    raise ValueError(
                        f"Unknown dependency '{dep_name}' for component '{name}' "
                        f"(parameter: '{param_name}')"
                    )
                
                dep_info = self._components[dep_name]
                
                # Фильтр зависимостей по стратегии
                if include_only_strategy_deps:
                    if dep_info.strategy != info.strategy:
                        continue
                
                # Рекурсивно обходим зависимость
                dfs(dep_name)
            
            # Помечаем как обработанный
            visited.add(name)
            
            # Callback после обхода всех зависимостей (для топологической сортировки)
            if on_complete:
                on_complete(name, info)
            else:
                result.append(name)
            
            # Завершаем отслеживание пути
            if check_cycles:
                temp_visited.remove(name)
                cycle_path.pop()
        
        # Определяем стартовые узлы
        if start_nodes is None:
            start_nodes = list(self._components.keys())
        
        # Запускаем обход
        for name in start_nodes:
            if name not in visited:
                dfs(name)
        
        return result

    def validate_dependency_graph(self):
        """
        Валидирует граф зависимостей компонентов.
        
        Проверяет:
        1. Циклические зависимости - обнаруживает циклы в графе
        2. Неизвестные зависимости - проверяет, что все зависимости зарегистрированы
        3. Правила зависимостей - SINGLETON не может зависеть от REQUEST
        
        Вызывает RuntimeError с описанием проблемы, если граф невалиден.
        """
        def validate_visit(name: ComponentName, info: ComponentInfo):
            """Валидация при посещении компонента."""
            # Проверяем все зависимости компонента
            for param_name, dep_name in info.dependencies.items():
                dep_info = self._components.get(dep_name)
                if dep_info is None:
                    # Уже проверено в _traverse_dependency_graph
                    continue
                
                # Проверка правил зависимостей
                # SINGLETON не может зависеть от REQUEST (защита от утечек)
                if info.strategy == ComponentStrategy.SINGLETON and dep_info.strategy == ComponentStrategy.REQUEST:
                    raise RuntimeError(
                        f"SINGLETON component '{name}' cannot depend on REQUEST component '{dep_name}'. "
                        f"This would cause request-scoped state to leak into singleton scope."
                    )
        
        # Обходим все компоненты с проверкой циклов и валидацией зависимостей
        self._traverse_dependency_graph(
            start_nodes=None,
            strategy_filter=None,
            check_cycles=True,
            include_only_strategy_deps=False,
            on_visit=validate_visit,
            on_complete=None,
        )
        

    def get_component(
        self, 
        component_name: ComponentName,
        scope: Optional[ScopeCache] = None,
    ) -> Component:
        """
        Получает компонент по имени.
        
        Для SINGLETON:
        - Проверяет в self._instances
        - Если нет - создает экземпляр (без запуска)
        - Возвращает компонент
        
        Для REQUEST:
        - Использует scope (кэш компонентов request scope)
        - Если scope не передан - пытается получить из scope_getter
        - Если компонент уже в кэше - возвращает его
        - Если нет - создает экземпляр (без запуска) и добавляет в кэш
        - Запуск компонентов происходит в RequestScope.__aenter__
        """
        if component_name not in self._components:
            raise ValueError(f"Unknown component '{component_name}'")
        
        info = self._components[component_name]
        
        # SINGLETON компоненты
        if info.strategy == ComponentStrategy.SINGLETON:
            if component_name in self._instances:
                return self._instances[component_name]
            
            # Создаем новый экземпляр (без запуска)
            inst = info.component_type()
            inst.set_app(self.app)
            
            # Собираем конфиг с зависимостями
            # Для SINGLETON: зависимости уже запущены, т.к. запускаем в топологическом порядке
            cfg = self._build_config_with_dependencies(component_name, info, scope=None)
            inst.set_config(cfg)
            self._instances[component_name] = inst
            return inst
        
        # REQUEST компоненты
        if info.strategy == ComponentStrategy.REQUEST:
            # Получаем scope (переданный или из ContextVar)
            if scope is None:
                scope = self._get_scope()
            
            if scope is None:
                raise RuntimeError(
                    f"REQUEST component '{component_name}' can only be accessed within request scope"
                )
            
            # Если компонент уже в кэше - возвращаем его
            if component_name in scope:
                return scope[component_name]
            
            # Создаем новый экземпляр (без запуска)
            # Запуск произойдет в RequestScope.__aenter__ для всех компонентов сразу
            inst = info.component_type()
            inst.set_app(self.app)
            
            # Собираем конфиг с зависимостями
            cfg = self._build_config_with_dependencies(component_name, info, scope=scope)
            inst.set_config(cfg)
            scope[component_name] = inst
            return inst
        
        raise RuntimeError(f"Unknown component strategy: {info.strategy}")

    def _build_config_with_dependencies(
        self,
        component_name: ComponentName,
        info: ComponentInfo,
        scope: Optional[ScopeCache] = None,
    ) -> Dict[str, Any]:
        """
        Собирает конфиг компонента с инъекцией зависимостей (.obj).
        
        Правила зависимостей уже проверены в validate_dependency_graph().
        
        Args:
            component_name: Имя компонента
            info: Информация о компоненте
            scope: Кэш REQUEST компонентов (если компонент REQUEST)
        
        Returns:
            Конфиг с инъектированными зависимостями
        
        Raises:
            RuntimeError: Если зависимость не запущена
        """
        cfg = (info.config or {}).copy()
        
        for param_name, dep_name in info.dependencies.items():
            if dep_name not in self._components:
                raise ValueError(f"Unknown dependency '{dep_name}' for component '{component_name}'")
            
            dep_info = self._components[dep_name]
            
            # Получаем зависимость (правила стратегий уже проверены в validate_dependency_graph)
            if dep_info.strategy == ComponentStrategy.SINGLETON:
                # SINGLETON зависимость - из _instances
                dep_comp = self.get_component(dep_name)
            else:
                # REQUEST зависимость - из scope
                if scope is None:
                    raise RuntimeError(
                        f"REQUEST component '{component_name}' cannot resolve REQUEST dependency "
                        f"'{dep_name}' without scope"
                    )
                if dep_name in scope:
                    dep_comp = scope[dep_name]
                else:
                    # Зависимость еще не создана - создаем рекурсивно
                    dep_comp = self.get_component(dep_name, scope=scope)
            
            # Зависимость должна быть запущена
            if not dep_comp.started:
                raise RuntimeError(
                    f"Dependency '{dep_name}' for component '{component_name}' is not started. "
                    f"All dependencies must be started before creating dependent component."
                )
            
            # Инъектируем .obj запущенной зависимости
            cfg[param_name] = dep_comp.obj
        
        return cfg

    def get_dependencies_topological_order(
        self, 
        component_name: ComponentName,
        strategy_filter: Optional[ComponentStrategy] = None,
    ) -> List[ComponentName]:
        """
        Возвращает топологически отсортированный список зависимостей для конкретного компонента.
        
        Включает все транзитивные зависимости компонента в топологическом порядке.
        Если A зависит от B, а B зависит от C, то результат будет: [C, B].
        
        Args:
            component_name: Имя компонента для получения зависимостей.
            strategy_filter: Если указан, возвращает только зависимости этой стратегии.
                            Если None, возвращает все зависимости независимо от стратегии.
        
        Returns:
            Список имен зависимостей в топологическом порядке (без самого компонента).
            Зависимости идут в порядке: сначала зависимости зависимостей, потом прямые зависимости.
        
        Пример:
            Если есть: component -> A -> B, component -> C
            Результат: [B, A, C]
        """
        # Проверяем существование компонента
        if component_name not in self._components:
            raise ValueError(f"Unknown component '{component_name}'")
        
        info = self._components[component_name]
        result: List[ComponentName] = []
        
        def on_complete(name: ComponentName, info: ComponentInfo):
            """
            Добавляем компонент в результат после обхода всех его зависимостей.
            Не добавляем сам стартовый компонент и применяем фильтр по стратегии.
            """
            if name != component_name:
                # Применяем фильтр по стратегии к результату
                if strategy_filter is None or info.strategy == strategy_filter:
                    result.append(name)
        
        # Обходим зависимости компонента, начиная с него
        # Важно: НЕ используем strategy_filter в _traverse_dependency_graph,
        # чтобы обойти все зависимости, а фильтруем результат в on_complete
        # Циклы не проверяем - они уже проверены при валидации
        self._traverse_dependency_graph(
            start_nodes=[component_name],
            strategy_filter=None,  # Обходим все зависимости
            check_cycles=False,  # Циклы уже проверены в validate_dependency_graph
            include_only_strategy_deps=False,  # Обходим все зависимости
            on_visit=None,
            on_complete=on_complete,
        )
        
        return result

    def get_topological_order(
        self,
        strategy: Optional[ComponentStrategy] = None,
    ) -> List[ComponentName]:
        """
        Возвращает все компоненты указанной стратегии в топологическом порядке.
        
        Топологический порядок гарантирует, что если компонент A зависит от компонента B,
        то B будет в списке раньше A. Это позволяет запускать компоненты в правильном порядке.
        
        Args:
            strategy: Стратегия компонентов для получения. 
                    Если None - возвращает все компоненты (не рекомендуется для запуска).
                    Если ComponentStrategy.SINGLETON - только SINGLETON компоненты.
                    Если ComponentStrategy.REQUEST - только REQUEST компоненты.
        
        Returns:
            Список имен компонентов в топологическом порядке.
            Компоненты без зависимостей идут первыми, компоненты с зависимостями - после них.
        
        Пример:
            Если есть: A -> B, B -> C (все SINGLETON)
            Результат: [C, B, A]
        """
        if strategy is None:
            raise ValueError("strategy must be specified (SINGLETON or REQUEST)")
        
        result: List[ComponentName] = []
        
        def on_complete(name: ComponentName, info: ComponentInfo):
            """Добавляем компонент в результат после обхода всех зависимостей."""
            result.append(name)
        
        # Находим все компоненты указанной стратегии
        filtered_nodes = [
            name for name, info in self._components.items()
            if info.strategy == strategy
        ]
        
        # Обходим компоненты указанной стратегии, игнорируя зависимости другой стратегии
        # Циклы не проверяем - они уже проверены при валидации
        self._traverse_dependency_graph(
            start_nodes=filtered_nodes,
            strategy_filter=strategy,
            check_cycles=False,  # Циклы уже проверены в validate_dependency_graph
            include_only_strategy_deps=True,  # Обходим только зависимости той же стратегии
            on_visit=None,
            on_complete=on_complete,
        )
        
        return result
