"""
Примеры использования библиотеки appkit.

Демонстрирует основные паттерны использования компонентной архитектуры.
"""

import asyncio
from typing import Optional
from adc_appkit import BaseApp, component, ComponentStrategy
from adc_appkit.components.component import Component
from adc_appkit.components.pg import PG


# ============ Пример 1: Простое приложение с SINGLETON компонентами ============

class Database:
    """Мок-класс для базы данных."""
    
    def __init__(self, host: str, port: int, database: str):
        self.host = host
        self.port = port
        self.database = database
        self._connected = False
    
    async def connect(self):
        """Подключается к базе данных."""
        self._connected = True
        print(f"Connected to {self.host}:{self.port}/{self.database}")
    
    async def disconnect(self):
        """Отключается от базы данных."""
        self._connected = False
        print(f"Disconnected from {self.host}:{self.port}/{self.database}")
    
    async def fetch(self, query: str):
        """Выполняет запрос."""
        if not self._connected:
            raise RuntimeError("Database not connected")
        print(f"Executing: {query}")
        return {"result": "data"}


class DatabaseComponent(Component[Database]):
    """Компонент для работы с базой данных."""
    
    async def _start(self, host: str, port: int, database: str, **kwargs) -> Database:
        """Создает и подключает базу данных."""
        db = Database(host, port, database)
        await db.connect()
        return db
    
    async def _stop(self) -> None:
        """Отключается от базы данных."""
        await self.obj.disconnect()
    
    async def is_alive(self) -> bool:
        """Проверяет соединение с базой данных."""
        return self.obj._connected


class SimpleApp(BaseApp):
    """Простое приложение с одним компонентом."""
    
    pg = component(DatabaseComponent, config_key="pg")
    
    async def business_logic(self):
        """Бизнес-логика приложения."""
        # Доступ к компоненту через дескриптор
        # pg - это Component[Database], нужно использовать .obj для доступа к Database
        return await self.pg.obj.fetch("SELECT 1")
    
    async def _stop(self):
        """Останавливает приложение (если нужно)."""
        pass


async def example_simple_app():
    """Пример использования простого приложения."""
    print("\n=== Пример 1: Простое приложение ===")
    
    config = {
        "pg": {
            "host": "localhost",
            "port": 5432,
            "database": "myapp"
        }
    }
    
    app = SimpleApp(components_config=config)
    
    # Запускаем приложение
    await app.start()
    
    # Используем бизнес-логику
    result = await app.business_logic()
    print(f"Result: {result}")
    
    # Проверяем здоровье
    health = await app.healthcheck()
    print(f"Health: {health}")
    
    # Останавливаем приложение
    await app.stop()


# ============ Пример 2: Приложение с зависимостями ============

class DAO:
    """Data Access Object для работы с данными."""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def fetch_users(self):
        """Получает пользователей из базы данных."""
        return await self.db.fetch("SELECT * FROM users")


class DAOComponent(Component[DAO]):
    """Компонент для DAO."""
    
    async def _start(self, db: Database, **kwargs) -> DAO:
        """Создает DAO с инъекцией Database."""
        return DAO(db)
    
    async def _stop(self) -> None:
        """Останавливает DAO."""
        pass
    
    async def is_alive(self) -> bool:
        """Проверяет здоровье DAO."""
        return True


class AppWithDependencies(BaseApp):
    """Приложение с зависимостями между компонентами."""
    
    pg = component(DatabaseComponent, config_key="pg")
    dao = component(DAOComponent, config_key="dao", dependencies={"db": "pg"})
    
    async def business_logic(self):
        """Бизнес-логика приложения."""
        # DAO уже имеет инъектированную Database
        return await self.dao.obj.fetch_users()
    
    async def _stop(self):
        """Останавливает приложение."""
        pass


async def example_app_with_dependencies():
    """Пример использования приложения с зависимостями."""
    print("\n=== Пример 2: Приложение с зависимостями ===")
    
    config = {
        "pg": {
            "host": "localhost",
            "port": 5432,
            "database": "myapp"
        },
        "dao": {}  # Пустой конфиг, все зависимости инъектируются автоматически
    }
    
    app = AppWithDependencies(components_config=config)
    
    # Запускаем приложение
    await app.start()
    
    # Используем бизнес-логику
    result = await app.business_logic()
    print(f"Result: {result}")
    
    # Останавливаем приложение
    await app.stop()


# ============ Пример 3: REQUEST компоненты ============

class UserService:
    """Сервис для работы с пользователями."""
    
    def __init__(self, dao: DAO, ctx: dict):
        self.dao = dao
        self.user_id = ctx.get("user_id")
        self.request_id = ctx.get("request_id")
    
    async def get_current_user(self):
        """Получает текущего пользователя."""
        return await self.dao.fetch_users()


class UserServiceComponent(Component[UserService]):
    """Компонент для UserService (REQUEST)."""
    
    async def _start(self, dao: DAO, ctx: dict, **kwargs) -> UserService:
        """Создает UserService с инъекцией DAO и контекста."""
        return UserService(dao, ctx)
    
    async def _stop(self) -> None:
        """Останавливает UserService."""
        pass
    
    async def is_alive(self) -> bool:
        """Проверяет здоровье UserService."""
        return True


class AppWithRequestComponents(BaseApp):
    """Приложение с REQUEST компонентами."""
    
    pg = component(DatabaseComponent, config_key="pg")
    dao = component(DAOComponent, config_key="dao", dependencies={"db": "pg"})
    user_service = component(
        UserServiceComponent,
        config_key="user_service",
        strategy=ComponentStrategy.REQUEST,
        dependencies={"dao": "dao"}
    )
    
    async def business_logic(self):
        """Бизнес-логика приложения."""
        # SINGLETON компоненты доступны напрямую
        return await self.dao.obj.fetch_users()
    
    async def request_handler(self, user_id: str, request_id: str):
        """Обработчик запроса с использованием REQUEST компонентов."""
        # REQUEST компоненты доступны через request_scope
        async with self.request_scope({"user_id": user_id, "request_id": request_id}) as req:
            # Получаем REQUEST компонент
            user_service = req.use("user_service")
            return await user_service.get_current_user()
    
    async def _stop(self):
        """Останавливает приложение."""
        pass


async def example_app_with_request_components():
    """Пример использования приложения с REQUEST компонентами."""
    print("\n=== Пример 3: REQUEST компоненты ===")
    
    config = {
        "pg": {
            "host": "localhost",
            "port": 5432,
            "database": "myapp"
        },
        "dao": {},
        "user_service": {}  # Контекст передается через request_scope
    }
    
    app = AppWithRequestComponents(components_config=config)
    
    # Запускаем приложение (SINGLETON компоненты)
    await app.start()
    
    # Обрабатываем запрос (REQUEST компоненты создаются и запускаются в контексте)
    result = await app.request_handler(user_id="user-123", request_id="req-456")
    print(f"Result: {result}")
    
    # Останавливаем приложение
    await app.stop()


# ============ Пример 4: Исправленный пример пользователя ============

class App(BaseApp):
    """Пример приложения от пользователя (исправленный)."""
    
    pg = component(PG, config_key="pg")
    # dao нужен как компонент, если используется
    # dao = component(DAOComponent, config_key="dao", dependencies={"db": "pg"})
    
    async def business_logic(self):
        """Бизнес-логика приложения."""
        # pg - это Component[Database], нужно использовать .obj для доступа к Database
        # Если pg это PG компонент, то self.pg.obj будет объектом базы данных
        return await self.pg.obj.fetch("SELECT 1")
    
    async def _stop(self):
        """Останавливает приложение."""
        pass


async def example_user_app():
    """Пример использования приложения пользователя."""
    print("\n=== Пример 4: Исправленный пример пользователя ===")
    
    # Предполагаем, что PG - это компонент из adc_appkit.components.pg
    # Но нужно проверить его интерфейс
    
    config = {
        "pg": {
            "host": "localhost",
            "port": 5432,
            "database": "myapp",
            # Другие параметры для PG компонента
        }
    }
    
    app = App(components_config=config)
    
    # Запускаем приложение
    await app.start()
    
    # Используем бизнес-логику
    try:
        result = await app.business_logic()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Останавливаем приложение
    await app.stop()


# ============ Запуск всех примеров ============

async def main():
    """Запускает все примеры."""
    try:
        await example_simple_app()
        await example_app_with_dependencies()
        await example_app_with_request_components()
        # await example_user_app()  # Раскомментировать если нужен
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

