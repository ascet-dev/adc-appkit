"""
Тесты архитектуры ADC AppKit.

Этот модуль содержит unit-тесты для проверки корректности работы
всех компонентов архитектуры без внешних зависимостей.
"""

import pytest
import asyncio
from typing import Dict, Any

from adc_appkit import BaseApp, component, ComponentStrategy
from adc_appkit.components.component import Component


# ======================= Мок-компоненты для тестирования =======================

class MockObject:
    def __init__(self, **kwargs):
        self.config = kwargs
        self.closed = False
    
    async def close(self):
        self.closed = True


class MockComponent(Component[MockObject]):
    async def _start(self, **kwargs) -> MockObject:
        return MockObject(**kwargs)

    async def _stop(self) -> None:
        await self.obj.close()

    async def is_alive(self) -> bool:
        return not self.obj.closed


# ======================= Тестовые приложения =======================

class MockSimpleApp(BaseApp):
    """Тестовое простое приложение."""
    
    singleton_comp = component(
        MockComponent,
        strategy=ComponentStrategy.SINGLETON,
        config_key="singleton"
    )
    
    request_comp = component(
        MockComponent,
        strategy=ComponentStrategy.REQUEST,
        config_key="request"
    )


class MockComplexApp(BaseApp):
    """Тестовое сложное приложение с зависимостями."""
    
    comp1 = component(
        MockComponent,
        strategy=ComponentStrategy.SINGLETON,
        config_key="comp1"
    )
    
    comp2 = component(
        MockComponent,
        strategy=ComponentStrategy.SINGLETON,
        config_key="comp2",
        depends_on=["comp1"]
    )
    
    request_comp1 = component(
        MockComponent,
        strategy=ComponentStrategy.REQUEST,
        config_key="request1"
    )
    
    request_comp2 = component(
        MockComponent,
        strategy=ComponentStrategy.REQUEST,
        config_key="request2"
    )


# ======================= Тесты =======================

@pytest.mark.asyncio
async def test_simple_app_lifecycle():
    """Тест жизненного цикла простого приложения."""
    config = {
        "singleton": {"name": "singleton", "value": 1},
        "request": {"name": "request", "value": 2}
    }
    
    app = MockSimpleApp(components_config=config)
    
    try:
        await app.start()
        assert app._started_singletons == ["singleton_comp"]
        
        health = await app.healthcheck()
        assert health == {"singleton_comp": True}
        
    finally:
        await app.stop()
        assert app._started_singletons == []


@pytest.mark.asyncio
async def test_singleton_component():
    """Тест singleton компонентов."""
    config = {
        "singleton": {"name": "singleton", "value": 1},
        "request": {"name": "request", "value": 2}
    }
    
    app = MockSimpleApp(components_config=config)
    
    try:
        await app.start()
        
        # Singleton компоненты должны быть одинаковыми экземплярами
        singleton1 = app.singleton_comp
        singleton2 = app.singleton_comp
        assert singleton1 is singleton2
        
        # Компонент должен быть запущен
        assert singleton1.started
        assert singleton1.obj.config == {"name": "singleton", "value": 1}
        
    finally:
        await app.stop()


@pytest.mark.asyncio
async def test_request_scope():
    """Тест request scope."""
    config = {
        "singleton": {"name": "singleton", "value": 1},
        "request": {"name": "request", "value": 2}
    }
    
    app = MockSimpleApp(components_config=config)
    
    try:
        await app.start()
        
        async with app.request_scope() as req:
            # Request компоненты в одном scope должны быть одинаковыми
            request1 = req.request_comp
            request2 = req.request_comp
            assert request1 is request2
            
            # Компонент должен быть создан, но не запущен
            assert not request1.started
            
            # Запускаем компонент
            await request1.start()
            assert request1.started
            assert request1.obj.config == {"name": "request", "value": 2}
        
        # После выхода из scope компонент должен быть закрыт
        assert request1._obj.closed
        
    finally:
        await app.stop()


@pytest.mark.asyncio
async def test_complex_app_dependencies():
    """Тест сложного приложения с зависимостями."""
    config = {
        "comp1": {"name": "component1", "value": 10},
        "comp2": {"name": "component2", "value": 20},
        "request1": {"name": "request1", "value": 30},
        "request2": {"name": "request2", "value": 40}
    }
    
    app = MockComplexApp(components_config=config)
    
    try:
        await app.start()
        
        # Проверяем порядок запуска (comp1 должен быть запущен первым)
        assert app._started_singletons == ["comp1", "comp2"]
        
        health = await app.healthcheck()
        assert health == {"comp1": True, "comp2": True}
        
        # Проверяем, что компоненты запущены
        assert app.comp1.started
        assert app.comp2.started
        assert app.comp1.obj.config == {"name": "component1", "value": 10}
        assert app.comp2.obj.config == {"name": "component2", "value": 20}
        
    finally:
        await app.stop()


@pytest.mark.asyncio
async def test_dependency_order():
    """Тест порядка зависимостей."""
    config = {
        "comp1": {"name": "first"},
        "comp2": {"name": "second"},
        "request1": {"name": "req1"},
        "request2": {"name": "req2"}
    }
    
    app = MockComplexApp(components_config=config)
    
    # Проверяем порядок зависимостей
    order = app._container.get_dependency_order()
    assert order == ["comp1", "comp2", "request_comp1", "request_comp2"]
    
    # comp2 должен идти после comp1 из-за зависимости
    comp1_index = order.index("comp1")
    comp2_index = order.index("comp2")
    assert comp1_index < comp2_index


@pytest.mark.asyncio
async def test_multiple_request_components():
    """Тест нескольких request компонентов в одном scope."""
    config = {
        "comp1": {"name": "first"},
        "comp2": {"name": "second"},
        "request1": {"name": "req1"},
        "request2": {"name": "req2"}
    }
    
    app = MockComplexApp(components_config=config)
    
    try:
        await app.start()
        
        async with app.request_scope() as req:
            req1 = req.request_comp1
            req2 = req.request_comp2
            
            # Запускаем компоненты
            await req1.start()
            await req2.start()
            
            # Проверяем конфигурации
            assert req1.obj.config == {"name": "req1"}
            assert req2.obj.config == {"name": "req2"}
            
            # Проверяем, что это разные экземпляры
            assert req1 is not req2
        
    finally:
        await app.stop()


@pytest.mark.asyncio
async def test_healthcheck():
    """Тест healthcheck функциональности."""
    config = {
        "singleton": {"name": "singleton", "value": 1},
        "request": {"name": "request", "value": 2}
    }
    
    app = MockSimpleApp(components_config=config)
    
    try:
        await app.start()
        
        # Health check должен возвращать только singleton компоненты
        health = await app.healthcheck()
        assert "singleton_comp" in health
        assert health["singleton_comp"] is True
        
        # Request компоненты не должны быть в health check
        assert "request_comp" not in health
        
    finally:
        await app.stop()


@pytest.mark.asyncio
async def test_component_configuration():
    """Тест конфигурации компонентов."""
    config = {
        "singleton": {"custom": "value", "number": 42},
        "request": {"another": "config"}
    }
    
    app = MockSimpleApp(components_config=config)
    
    try:
        await app.start()
        
        # Проверяем, что конфигурация передается корректно
        singleton = app.singleton_comp
        assert singleton.obj.config == {"custom": "value", "number": 42}
        
        async with app.request_scope() as req:
            request = req.request_comp
            await request.start()
            assert request.obj.config == {"another": "config"}
        
    finally:
        await app.stop()


@pytest.mark.asyncio
async def test_app_stop_cleanup():
    """Тест очистки ресурсов при остановке приложения."""
    config = {
        "singleton": {"name": "singleton", "value": 1},
        "request": {"name": "request", "value": 2}
    }
    
    app = MockSimpleApp(components_config=config)
    
    await app.start()
    singleton = app.singleton_comp
    
    # Компонент должен быть запущен
    assert singleton.started
    assert not singleton.obj.closed
    
    await app.stop()
    
    # После остановки компонент должен быть закрыт
    assert singleton._obj.closed
    assert not singleton.started
