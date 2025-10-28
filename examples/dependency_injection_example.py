"""
Пример использования зависимостей в ADC AppKit.

Демонстрирует новый механизм проброса зависимостей между компонентами
с поддержкой именованных параметров.
"""

import asyncio
from typing import Dict, Any

from adc_appkit import BaseApp, component, ComponentStrategy, create_component
from adc_appkit.components.component import Component


# ======================= Мок-компоненты для демонстрации =======================

class DatabaseConnection:
    """Мок подключения к базе данных."""
    
    def __init__(self, host: str, port: int, database: str, **kwargs):
        self.host = host
        self.port = port
        self.database = database
        self.config = kwargs
        self.closed = False
        print(f"DatabaseConnection created: {host}:{port}/{database}")
    
    async def query(self, sql: str) -> str:
        return f"Query '{sql}' executed on {self.host}:{self.port}/{self.database}"
    
    async def close(self):
        self.closed = True
        print(f"DatabaseConnection closed: {self.host}:{self.port}/{self.database}")


class HTTPClient:
    """Мок HTTP клиента."""
    
    def __init__(self, base_url: str, timeout: int = 30, **kwargs):
        self.base_url = base_url
        self.timeout = timeout
        self.config = kwargs
        self.closed = False
        print(f"HTTPClient created: {base_url} (timeout={timeout})")
    
    async def get(self, url: str) -> str:
        return f"GET {self.base_url}{url} - timeout={self.timeout}"
    
    async def close(self):
        self.closed = True
        print(f"HTTPClient closed: {self.base_url}")


class CacheService:
    """Мок сервиса кэширования."""
    
    def __init__(self, redis_url: str, ttl: int = 3600, **kwargs):
        self.redis_url = redis_url
        self.ttl = ttl
        self.config = kwargs
        self.closed = False
        print(f"CacheService created: {redis_url} (ttl={ttl})")
    
    async def get(self, key: str) -> str:
        return f"Cache GET {key} from {self.redis_url}"
    
    async def set(self, key: str, value: str) -> str:
        return f"Cache SET {key}={value} in {self.redis_url} (ttl={self.ttl})"
    
    async def close(self):
        self.closed = True
        print(f"CacheService closed: {self.redis_url}")


class UserService:
    """Сервис пользователей с зависимостями."""
    
    def __init__(self, db, http, cache, **kwargs):
        # Зависимости приходят как объекты из запущенных компонентов
        self.db = db
        self.http = http
        self.cache = cache
        self.config = kwargs
        print(f"UserService created with dependencies: db={db.host}, http={http.base_url}, cache={cache.redis_url}")
    
    async def get_user(self, user_id: int) -> str:
        # Проверяем кэш
        cache_key = f"user:{user_id}"
        cached = await self.cache.get(cache_key)
        print(f"Cache check: {cached}")
        
        # Если нет в кэше, идем в БД
        db_result = await self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
        print(f"DB query: {db_result}")
        
        # Кэшируем результат
        await self.cache.set(cache_key, f"user_data_{user_id}")
        
        # Можем также вызвать внешний API
        api_result = await self.http.get(f"/users/{user_id}")
        print(f"API call: {api_result}")
        
        return f"User {user_id} data from {self.db.host} via {self.http.base_url}"


# ======================= Компоненты =======================

class Database(Component[DatabaseConnection]):
    async def _start(self, **kwargs) -> DatabaseConnection:
        return DatabaseConnection(**kwargs)
    
    async def _stop(self) -> None:
        await self.obj.close()
    
    async def is_alive(self) -> bool:
        return not self.obj.closed


class HTTP(Component[HTTPClient]):
    async def _start(self, **kwargs) -> HTTPClient:
        return HTTPClient(**kwargs)
    
    async def _stop(self) -> None:
        await self.obj.close()
    
    async def is_alive(self) -> bool:
        return not self.obj.closed


class Cache(Component[CacheService]):
    async def _start(self, **kwargs) -> CacheService:
        return CacheService(**kwargs)
    
    async def _stop(self) -> None:
        await self.obj.close()
    
    async def is_alive(self) -> bool:
        return not self.obj.closed


class UserServiceComponent(Component[UserService]):
    async def _start(self, **kwargs) -> UserService:
        return UserService(**kwargs)
    
    async def _stop(self) -> None:
        # UserService не требует явного закрытия
        pass
    
    async def is_alive(self) -> bool:
        return True


# ======================= Приложение с зависимостями =======================

class DependencyInjectionApp(BaseApp):
    """Приложение с демонстрацией проброса зависимостей."""
    
    # Базовые компоненты
    database = component(
        Database,
        strategy=ComponentStrategy.SINGLETON,
        config_key="database"
    )
    
    http_client = component(
        HTTP,
        strategy=ComponentStrategy.SINGLETON,
        config_key="http"
    )
    
    cache = component(
        Cache,
        strategy=ComponentStrategy.SINGLETON,
        config_key="cache"
    )
    
    # Сервис с именованными зависимостями
    user_service = component(
        UserServiceComponent,
        strategy=ComponentStrategy.SINGLETON,
        config_key="user_service",
        dependencies={
            "db": "database",      # параметр db получает компонент database
            "http": "http_client", # параметр http получает компонент http_client
            "cache": "cache"       # параметр cache получает компонент cache
        }
    )
    
    async def business_logic(self):
        """Демонстрация работы с зависимостями."""
        
        print("=== Dependency Injection Demo ===")
        
        # Получаем сервис пользователей
        user_service = self.user_service
        print(f"User service component: {user_service}")
        
        # Запускаем сервис (автоматически запустятся все зависимости)
        await user_service.start()
        
        # Используем сервис
        result = await user_service.obj.get_user(123)
        print(f"User service result: {result}")
        
        # Проверяем, что все зависимости запущены
        print(f"Database started: {self.database.started}")
        print(f"HTTP client started: {self.http_client.started}")
        print(f"Cache started: {self.cache.started}")


# ======================= Пример с create_component =======================

class SimpleDataProcessor:
    """Простой обработчик данных."""
    
    def __init__(self, db, cache, batch_size: int = 100, **kwargs):
        # Зависимости приходят как объекты из запущенных компонентов
        self.db = db
        self.cache = cache
        self.batch_size = batch_size
        self.config = kwargs
        print(f"SimpleDataProcessor created: batch_size={batch_size}, db={db.host}, cache={cache.redis_url}")
    
    async def process_data(self, data: list) -> str:
        # Кэшируем данные
        cache_key = f"processed_data_{len(data)}"
        await self.cache.set(cache_key, f"processed_{len(data)}_items")
        
        # Сохраняем в БД
        result = await self.db.query(f"INSERT INTO processed_data VALUES ({len(data)})")
        
        return f"Processed {len(data)} items (batch_size={self.batch_size}): {result}"


class CreateComponentApp(BaseApp):
    """Приложение с компонентами, созданными через create_component."""
    
    # Базовые компоненты
    database = component(
        Database,
        strategy=ComponentStrategy.SINGLETON,
        config_key="database"
    )
    
    cache = component(
        Cache,
        strategy=ComponentStrategy.SINGLETON,
        config_key="cache"
    )
    
    # Компонент, созданный на лету с зависимостями
    data_processor = component(
        create_component(SimpleDataProcessor),
        strategy=ComponentStrategy.REQUEST,
        config_key="data_processor",
        dependencies={
            "db": "database",
            "cache": "cache"
        }
    )
    
    async def business_logic(self):
        """Демонстрация работы с create_component и зависимостями."""
        
        print("=== Create Component with Dependencies Demo ===")
        
        # Используем в request scope
        async with self.request_scope() as req:
            # Получаем процессор
            processor = req.data_processor
            print(f"Data processor component: {processor}")
            
            # Запускаем процессор
            await processor.start()
            
            # Используем процессор
            result = await processor.obj.process_data(["item1", "item2", "item3"])
            print(f"Data processor result: {result}")


# ======================= Функции для запуска примеров =======================

async def run_dependency_injection_demo():
    """Запуск демонстрации проброса зависимостей."""
    
    config = {
        "database": {
            "host": "localhost",
            "port": 5432,
            "database": "myapp",
            "user": "postgres",
            "password": "secret"
        },
        "http": {
            "base_url": "https://api.example.com",
            "timeout": 30,
            "retries": 3
        },
        "cache": {
            "redis_url": "redis://localhost:6379",
            "ttl": 3600,
            "max_connections": 10
        },
        "user_service": {
            "debug": True,
            "log_level": "INFO"
        }
    }
    
    app = DependencyInjectionApp(components_config=config)
    
    try:
        print("Starting dependency injection demo...")
        await app.start()
        
        print("App health:", await app.healthcheck())
        
        await app.business_logic()
        
    finally:
        print("Stopping dependency injection demo...")
        await app.stop()


async def run_create_component_demo():
    """Запуск демонстрации create_component с зависимостями."""
    
    config = {
        "database": {
            "host": "analytics-db.example.com",
            "port": 5432,
            "database": "analytics",
            "user": "analytics",
            "password": "analytics_secret"
        },
        "cache": {
            "redis_url": "redis://analytics-cache:6379",
            "ttl": 7200,
            "max_connections": 20
        },
        "data_processor": {
            "batch_size": 200,
            "timeout": 60,
            "debug": True
        }
    }
    
    app = CreateComponentApp(components_config=config)
    
    try:
        print("Starting create component demo...")
        await app.start()
        
        print("App health:", await app.healthcheck())
        
        await app.business_logic()
        
    finally:
        print("Stopping create component demo...")
        await app.stop()


async def main():
    """Главная функция для запуска примеров."""
    
    print("=== ADC AppKit Dependency Injection Examples ===\n")
    
    # Демонстрация именованных зависимостей
    print("=== Named Dependencies Demo ===")
    await run_dependency_injection_demo()
    
    print("\n" + "="*60 + "\n")
    
    # Демонстрация create_component с зависимостями
    print("=== Create Component with Dependencies Demo ===")
    await run_create_component_demo()


if __name__ == "__main__":
    asyncio.run(main())
