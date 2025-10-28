"""
Тесты для функции create_component.

Этот модуль содержит unit-тесты для проверки корректности работы
функции create_component для создания компонентов на лету.
"""

import asyncio
from typing import Dict, Any

from adc_appkit import BaseApp, component, ComponentStrategy, create_component
from adc_appkit.components.component import Component


# ======================= Мок-объекты для тестирования =======================

class MockService:
    """Мок-сервис для тестирования create_component."""
    
    def __init__(self, name: str, version: str = "1.0.0", **kwargs):
        self.name = name
        self.version = version
        self.config = kwargs
        self.closed = False
    
    async def process(self, data: str) -> str:
        return f"{self.name} v{self.version} processed: {data}"
    
    async def close(self):
        self.closed = True
    
    async def is_alive(self) -> bool:
        return not self.closed


class MockDataProcessor:
    """Мок-процессор данных для тестирования."""
    
    def __init__(self, batch_size: int = 100, timeout: int = 30, **kwargs):
        self.batch_size = batch_size
        self.timeout = timeout
        self.config = kwargs
        self.closed = False
    
    async def process_batch(self, items: list) -> list:
        return [f"Processed: {item} (batch_size={self.batch_size})" for item in items]
    
    def close(self):  # Синхронный close
        self.closed = True


class MockSimpleObject:
    """Простой мок-объект без методов close/is_alive."""
    
    def __init__(self, **kwargs):
        self.config = kwargs


# ======================= Кастомные компоненты для тестирования =======================

class CustomComponent(Component[MockService]):
    """Кастомный компонент для сравнения с create_component."""
    
    async def _start(self, **kwargs) -> MockService:
        return MockService(**kwargs)
    
    async def _stop(self) -> None:
        await self.obj.close()
    
    async def is_alive(self) -> bool:
        return await self.obj.is_alive()


# ======================= Тестовые приложения =======================

class CreateComponentTestApp(BaseApp):
    """Тестовое приложение для create_component."""
    
    # Компонент с create_component
    service1 = component(
        create_component(MockService),
        strategy=ComponentStrategy.SINGLETON,
        config_key="service1"
    )
    
    # Компонент с create_component для request scope
    service2 = component(
        create_component(MockDataProcessor),
        strategy=ComponentStrategy.REQUEST,
        config_key="service2"
    )
    
    # Кастомный компонент для сравнения
    custom_service = component(
        CustomComponent,
        strategy=ComponentStrategy.SINGLETON,
        config_key="custom_service"
    )
    
    # Простой компонент без методов close/is_alive
    simple_comp = component(
        create_component(MockSimpleObject),
        strategy=ComponentStrategy.SINGLETON,
        config_key="simple_comp"
    )


# ======================= Тесты =======================

async def test_create_component_basic():
    """Тест базовой функциональности create_component."""
    config = {
        "service1": {
            "name": "TestService",
            "version": "2.0.0",
            "debug": True
        },
        "service2": {
            "batch_size": 100,
            "timeout": 30
        },
        "custom_service": {
            "name": "CustomService",
            "version": "1.0.0"
        },
        "simple_comp": {
            "param1": "value1"
        }
    }
    
    app = CreateComponentTestApp(components_config=config)
    
    try:
        await app.start()
        
        # Тестируем создание и запуск компонента
        service1 = app.service1
        await service1.start()
        
        assert service1.obj.name == "TestService"
        assert service1.obj.version == "2.0.0"
        assert service1.obj.config["debug"] is True
        
        # Тестируем функциональность
        result = await service1.obj.process("test data")
        assert "TestService v2.0.0 processed: test data" in result
        
        # Тестируем health check
        assert await service1.is_alive() is True
        
    finally:
        await app.stop()


async def test_create_component_without_methods():
    """Тест create_component с объектом без методов close/is_alive."""
    config = {
        "service1": {
            "name": "TestService",
            "version": "1.0.0"
        },
        "service2": {
            "batch_size": 100,
            "timeout": 30
        },
        "custom_service": {
            "name": "CustomService",
            "version": "1.0.0"
        },
        "simple_comp": {
            "param1": "value1",
            "param2": "value2"
        }
    }
    
    app = CreateComponentTestApp(components_config=config)
    
    try:
        await app.start()
        
        simple_comp = app.simple_comp
        await simple_comp.start()
        
        assert simple_comp.obj.config["param1"] == "value1"
        assert simple_comp.obj.config["param2"] == "value2"
        
        # Тестируем health check (должен возвращать True по умолчанию)
        assert await simple_comp.is_alive() is True
        
    finally:
        await app.stop()


async def test_custom_component_comparison():
    """Тест сравнения create_component с кастомным компонентом."""
    config = {
        "service1": {
            "name": "TestService",
            "version": "1.0.0"
        },
        "service2": {
            "batch_size": 100,
            "timeout": 30
        },
        "custom_service": {
            "name": "CustomService",
            "version": "3.0.0",
            "debug": False
        },
        "simple_comp": {
            "param1": "value1"
        }
    }
    
    app = CreateComponentTestApp(components_config=config)
    
    try:
        await app.start()
        
        custom_service = app.custom_service
        await custom_service.start()
        
        assert custom_service.obj.name == "CustomService"
        assert custom_service.obj.version == "3.0.0"
        assert custom_service.obj.config["debug"] is False
        
        # Тестируем функциональность
        result = await custom_service.obj.process("custom data")
        assert "CustomService v3.0.0 processed: custom data" in result
        
        # Тестируем health check
        assert await custom_service.is_alive() is True
        
    finally:
        await app.stop()


async def test_create_component_request_scope():
    """Тест create_component в request scope."""
    config = {
        "service1": {
            "name": "TestService",
            "version": "1.0.0"
        },
        "service2": {
            "batch_size": 50,
            "timeout": 60,
            "debug": True
        },
        "custom_service": {
            "name": "CustomService",
            "version": "1.0.0"
        },
        "simple_comp": {
            "param1": "value1"
        }
    }
    
    app = CreateComponentTestApp(components_config=config)
    
    try:
        await app.start()
        
        # Тестируем в request scope
        async with app.request_scope() as req:
            service2 = req.service2
            await service2.start()
            
            assert service2.obj.batch_size == 50
            assert service2.obj.timeout == 60
            assert service2.obj.config["debug"] is True
            
            # Тестируем функциональность
            result = await service2.obj.process_batch(["item1", "item2"])
            assert len(result) == 2
            assert "Processed: item1 (batch_size=50)" in result[0]
            assert "Processed: item2 (batch_size=50)" in result[1]
            
    finally:
        await app.stop()


async def test_create_component_sync_close():
    """Тест create_component с синхронным методом close."""
    config = {
        "service1": {
            "name": "TestService",
            "version": "1.0.0"
        },
        "service2": {
            "batch_size": 25,
            "timeout": 45
        },
        "custom_service": {
            "name": "CustomService",
            "version": "1.0.0"
        },
        "simple_comp": {
            "param1": "value1"
        }
    }
    
    app = CreateComponentTestApp(components_config=config)
    
    try:
        await app.start()
        
        async with app.request_scope() as req:
            service2 = req.service2
            await service2.start()
            
            # Проверяем, что объект не закрыт
            assert not service2.obj.closed
            
            # Останавливаем компонент (должен вызвать синхронный close)
            await service2.stop()
            
            # Проверяем, что объект закрыт (через _obj, так как компонент остановлен)
            assert service2._obj.closed
            
    finally:
        await app.stop()


async def test_create_component_async_close():
    """Тест create_component с асинхронным методом close."""
    config = {
        "service1": {
            "name": "AsyncService",
            "version": "1.0.0"
        },
        "service2": {
            "batch_size": 100,
            "timeout": 30
        },
        "custom_service": {
            "name": "CustomService",
            "version": "1.0.0"
        },
        "simple_comp": {
            "param1": "value1"
        }
    }
    
    app = CreateComponentTestApp(components_config=config)
    
    try:
        await app.start()
        
        service1 = app.service1
        await service1.start()
        
        # Проверяем, что объект не закрыт
        assert not service1.obj.closed
        
        # Останавливаем компонент (должен вызвать асинхронный close)
        await service1.stop()
        
        # Проверяем, что объект закрыт (через _obj, так как компонент остановлен)
        assert service1._obj.closed
        
    finally:
        await app.stop()


async def test_create_component_class_naming():
    """Тест правильного именования классов в create_component."""
    # Создаем компонент
    TestComponent = create_component(MockService)
    
    # Проверяем, что имя класса правильно установлено
    assert TestComponent.__name__ == "Component[MockService]"
    assert TestComponent.__qualname__ == "Component[MockService]"
    
    # Проверяем, что это действительно подкласс Component
    assert issubclass(TestComponent, Component)
    
    # Проверяем, что можно создать экземпляр
    instance = TestComponent()
    assert isinstance(instance, Component)
    assert isinstance(instance, TestComponent)


async def test_create_component_simple_usage():
    """Тест простого использования create_component."""
    config = {
        "service1": {
            "name": "SimpleService",
            "version": "1.0.0"
        },
        "service2": {
            "batch_size": 100,
            "timeout": 30
        },
        "custom_service": {
            "name": "CustomService",
            "version": "1.0.0"
        },
        "simple_comp": {
            "param1": "value1"
        }
    }
    
    app = CreateComponentTestApp(components_config=config)
    
    try:
        await app.start()
        
        service1 = app.service1
        await service1.start()
        
        # Проверяем базовую функциональность
        assert service1.obj.name == "SimpleService"
        assert service1.obj.version == "1.0.0"
        
        # Тестируем обработку данных
        result = await service1.obj.process("simple data")
        assert "SimpleService v1.0.0 processed: simple data" in result
        
        # Тестируем health check
        assert await service1.is_alive() is True
        
    finally:
        await app.stop()


# ======================= Функция для запуска всех тестов =======================

async def run_all_tests():
    """Запуск всех тестов."""
    tests = [
        test_create_component_basic,
        test_create_component_without_methods,
        test_custom_component_comparison,
        test_create_component_request_scope,
        test_create_component_sync_close,
        test_create_component_async_close,
        test_create_component_class_naming,
        test_create_component_simple_usage,
    ]
    
    for test in tests:
        try:
            await test()
            print(f"✅ {test.__name__} passed")
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            raise
    
    print("🎉 All tests passed!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
