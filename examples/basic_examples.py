"""
Примеры использования ADC AppKit.

Этот модуль содержит практические примеры использования библиотеки
с мок-компонентами для демонстрации возможностей.
"""

import asyncio
from typing import Dict, Any

from adc_appkit import BaseApp, component, ComponentStrategy
from adc_appkit.components.component import Component


# ======================= Мок-компоненты для примеров =======================

class MockHTTPClient:
    def __init__(self, **kwargs):
        self.config = kwargs
        self.closed = False
    
    async def get(self, url: str) -> str:
        return f"GET {url} - {self.config}"
    
    async def close(self):
        self.closed = True


class MockDatabase:
    def __init__(self, **kwargs):
        self.config = kwargs
        self.closed = False
    
    async def fetch(self, query: str) -> str:
        return f"Query: {query} - {self.config}"
    
    async def close(self):
        self.closed = True


class MockS3Client:
    def __init__(self, **kwargs):
        self.config = kwargs
        self.closed = False
    
    async def upload(self, key: str, data: bytes) -> str:
        return f"Uploaded {key} - {self.config}"
    
    async def close(self):
        self.closed = True


# ======================= Компоненты =======================

class HTTP(Component[MockHTTPClient]):
    async def _start(self, **kwargs) -> MockHTTPClient:
        return MockHTTPClient(**kwargs)

    async def _stop(self) -> None:
        await self.obj.close()

    async def is_alive(self) -> bool:
        return not self.obj.closed


class PG(Component[MockDatabase]):
    async def _start(self, **kwargs) -> MockDatabase:
        return MockDatabase(**kwargs)

    async def _stop(self) -> None:
        await self.obj.close()

    async def is_alive(self) -> bool:
        return not self.obj.closed


class S3(Component[MockS3Client]):
    async def _start(self, **kwargs) -> MockS3Client:
        return MockS3Client(**kwargs)

    async def _stop(self) -> None:
        await self.obj.close()

    async def is_alive(self) -> bool:
        return not self.obj.closed


# ======================= Пример 1: Простое приложение =======================

class SimpleApp(BaseApp):
    """Простое приложение с базовыми компонентами."""
    
    # HTTP клиент - создается на каждый запрос
    http = component(
        HTTP,
        strategy=ComponentStrategy.REQUEST,
        config_key="http"
    )
    
    # PostgreSQL соединение - singleton
    pg = component(
        PG,
        strategy=ComponentStrategy.SINGLETON,
        config_key="pg",
        depends_on=[HTTP]  # PG может зависеть от HTTP для порядка старта
    )
    
    # S3 клиент - singleton
    s3 = component(
        S3,
        strategy=ComponentStrategy.SINGLETON,
        config_key="s3"
    )
    
    async def business_logic(self):
        """Пример бизнес-логики с использованием компонентов."""
        
        print("=== Simple App Business Logic ===")
        
        # ВНЕ scope — каждый доступ к app.http создаёт новый инстанс
        print("Outside request scope:")
        try:
            # Это создаст новый HTTP клиент
            http_client = self.http
            print(f"HTTP client created: {http_client}")
        except Exception as e:
            print(f"HTTP client error (expected): {e}")
        
        # ВНУТРИ scope — один инстанс на весь блок
        print("\nInside request scope:")
        async with self.request_scope() as req:
            # HTTP клиент создается один раз на весь scope
            http_client = req.http
            print(f"HTTP client in scope: {http_client}")
            
            # Запускаем HTTP клиент
            await http_client.start()
            
            # Тестируем функциональность
            result = await http_client.obj.get("https://example.com")
            print(f"HTTP GET result: {result}")
            
            # PG соединение доступно как singleton
            pg_pool = self.pg
            print(f"PG pool: {pg_pool}")
            
            # Тестируем функциональность
            query_result = await pg_pool.obj.fetch("SELECT 1")
            print(f"PG query result: {query_result}")
            
            # S3 клиент доступен как singleton
            s3_client = self.s3
            print(f"S3 client: {s3_client}")
            
            # Тестируем функциональность
            upload_result = await s3_client.obj.upload("test.txt", b"test data")
            print(f"S3 upload result: {upload_result}")


# ======================= Пример 2: Сложное приложение =======================

class ExternalAPI(HTTP):
    """Кастомный HTTP клиент для внешнего API."""
    
    async def call_api(self, endpoint: str) -> str:
        """Вызов внешнего API."""
        result = await self.obj.get(f"https://api.external.com{endpoint}")
        return f"External API call: {result}"


class ComplexApp(BaseApp):
    """Сложное приложение с несколькими компонентами одного типа."""
    
    # Несколько HTTP клиентов с разными конфигурациями
    main_http = component(
        HTTP, 
        strategy=ComponentStrategy.REQUEST, 
        config_key="main_http"
    )
    api_http = component(
        ExternalAPI, 
        strategy=ComponentStrategy.REQUEST, 
        config_key="api_http"
    )
    
    # Несколько PG соединений
    main_pg = component(
        PG,
        strategy=ComponentStrategy.SINGLETON,
        config_key="main_pg",
        depends_on=["main_http"],  # зависит от main_http
    )
    analytics_pg = component(
        PG,
        strategy=ComponentStrategy.SINGLETON,
        config_key="analytics_pg",
        depends_on=["api_http"],  # зависит от api_http
    )
    
    # S3 клиент
    s3 = component(
        S3,
        strategy=ComponentStrategy.SINGLETON,
        config_key="s3"
    )
    
    async def business_logic(self):
        """Пример бизнес-логики для сложного приложения."""
        
        print("=== Complex App Business Logic ===")
        
        # Использование разных HTTP клиентов в scope
        async with self.request_scope() as req:
            main_client = req.main_http
            api_client = req.api_http
            
            print(f"Main HTTP client: {main_client}")
            print(f"API HTTP client: {api_client}")
            
            # Запускаем HTTP клиенты
            await main_client.start()
            await api_client.start()
            
            # Тестируем функциональность
            main_result = await main_client.obj.get("https://api.main.com/users")
            print(f"Main API result: {main_result}")
            
            api_result = await api_client.call_api("/data")
            print(f"External API result: {api_result}")
            
            # Использование разных PG соединений
            main_pool = self.main_pg
            analytics_pool = self.analytics_pg
            
            print(f"Main PG pool: {main_pool}")
            print(f"Analytics PG pool: {analytics_pool}")
            
            # Тестируем функциональность
            main_query = await main_pool.obj.fetch("SELECT * FROM users")
            print(f"Main DB query: {main_query}")
            
            analytics_query = await analytics_pool.obj.fetch("SELECT COUNT(*) FROM events")
            print(f"Analytics DB query: {analytics_query}")
            
            # S3 клиент
            s3_client = self.s3
            print(f"S3 client: {s3_client}")
            
            # Тестируем функциональность
            s3_result = await s3_client.obj.upload("analytics.json", b'{"data": "test"}')
            print(f"S3 upload: {s3_result}")


# ======================= Функции для запуска примеров =======================

async def run_simple_app():
    """Запуск простого приложения."""
    
    # Конфигурация компонентов
    simple_config = {
        "http": {
            "timeout": 30,
            "base_url": "https://api.example.com",
        },
        "pg": {
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
        },
        "s3": {
            "bucket": "my-bucket",
            "region": "us-east-1",
        },
    }
    
    app = SimpleApp(components_config=simple_config)
    
    try:
        print("Starting simple app...")
        await app.start()
        
        print("Health check:", await app.healthcheck())
        
        await app.business_logic()
        
    finally:
        print("Stopping simple app...")
        await app.stop()


async def run_complex_app():
    """Запуск сложного приложения."""
    
    # Конфигурация для сложного приложения
    complex_config = {
        "main_http": {
            "timeout": 5, 
            "base_url": "https://api.main.com"
        },
        "api_http": {
            "timeout": 10, 
            "base_url": "https://api.external.com"
        },
        "main_pg": {
            "host": "main-db.example.com",
            "database": "main_db"
        },
        "analytics_pg": {
            "host": "analytics-db.example.com",
            "database": "analytics_db"
        },
        "s3": {
            "bucket": "analytics-bucket",
            "region": "us-west-2",
        }
    }
    
    app = ComplexApp(components_config=complex_config)
    
    try:
        print("\nStarting complex app...")
        await app.start()
        
        print("Complex app health:", await app.healthcheck())
        
        await app.business_logic()
        
    finally:
        print("Stopping complex app...")
        await app.stop()


async def main():
    """Главная функция для запуска примеров."""
    
    print("=== ADC AppKit Examples ===\n")
    
    # Запускаем простое приложение
    print("=== Simple App ===")
    await run_simple_app()
    
    # Запускаем сложное приложение
    print("\n=== Complex App ===")
    await run_complex_app()


if __name__ == "__main__":
    asyncio.run(main())
