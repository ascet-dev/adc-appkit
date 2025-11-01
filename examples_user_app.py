"""
Пример использования App класса от пользователя.

Показывает как правильно использовать компонент PG и как работать с бизнес-логикой.
"""

import asyncio
from adc_appkit import BaseApp, component
from adc_appkit.components.pg import PG


# ============ Пример 1: Базовая версия (исправленная) ============

class App(BaseApp):
    """Простое приложение с компонентом PG."""
    
    pg = component(PG, config_key="pg")
    
    async def business_logic(self):
        """
        Бизнес-логика приложения.
        
        Важно:
        - self.pg - это Component[Pool] (обертка)
        - self.pg.obj - это asyncpg.Pool (реальный объект)
        - Pool.fetch() возвращает корутину, нужен await
        """
        # Получаем объект базы данных из компонента
        pool = self.pg.obj  # это asyncpg.Pool
        
        # Выполняем запрос
        rows = await pool.fetch("SELECT 1")
        return rows
    
    async def _stop(self):
        """Останавливает приложение (необязательно, если нет дополнительной логики)."""
        pass


async def example_basic_app():
    """Пример использования базового App."""
    print("\n=== Пример 1: Базовый App ===")
    
    config = {
        "pg": {
            "host": "localhost",
            "port": 5432,
            "database": "myapp",
            "user": "user",
            "password": "password"
        }
    }
    
    app = App(components_config=config)
    
    try:
        # Запускаем приложение (инициализирует PG компонент)
        await app.start()
        print("App started")
        
        # Используем бизнес-логику
        result = await app.business_logic()
        print(f"Query result: {result}")
        
        # Проверяем здоровье
        health = await app.healthcheck()
        print(f"Health: {health}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Останавливаем приложение (закрывает соединения)
        await app.stop()
        print("App stopped")


# ============ Пример 2: С DAO компонентом ============

from asyncpg import Pool, Record
from typing import List


class DAO:
    """Data Access Object для работы с базой данных."""
    
    def __init__(self, pool: Pool):
        self.pool = pool
    
    async def fetch_users(self) -> List[Record]:
        """Получает всех пользователей."""
        return await self.pool.fetch("SELECT * FROM users")
    
    async def fetch_one(self, query: str, *args) -> Record:
        """Выполняет запрос и возвращает одну запись."""
        return await self.pool.fetchrow(query, *args)


class DAOComponent:
    """Компонент для DAO."""
    
    async def _start(self, pool: Pool, **kwargs) -> DAO:
        """Создает DAO с инъекцией Pool."""
        return DAO(pool)
    
    async def _stop(self) -> None:
        """Останавливает DAO."""
        pass
    
    async def is_alive(self) -> bool:
        """Проверяет здоровье DAO."""
        return True


# Нужно зарегистрировать DAOComponent как компонент
from adc_appkit.components.component import Component

class DAOComponentWrapper(Component[DAO]):
    """Обертка для DAOComponent."""
    
    async def _start(self, pool: Pool, **kwargs) -> DAO:
        return DAO(pool)
    
    async def _stop(self) -> None:
        pass
    
    async def is_alive(self) -> bool:
        return True


class AppWithDAO(BaseApp):
    """Приложение с DAO компонентом."""
    
    pg = component(PG, config_key="pg")
    dao = component(DAOComponentWrapper, config_key="dao", dependencies={"pool": "pg"})
    
    async def business_logic(self):
        """
        Бизнес-логика с использованием DAO.
        
        Важно:
        - self.pg.obj - это Pool
        - self.dao.obj - это DAO (с инъектированным Pool)
        """
        # Используем DAO для работы с базой данных
        users = await self.dao.obj.fetch_users()
        return users
    
    async def _stop(self):
        """Останавливает приложение."""
        pass


async def example_app_with_dao():
    """Пример использования App с DAO."""
    print("\n=== Пример 2: App с DAO ===")
    
    config = {
        "pg": {
            "host": "localhost",
            "port": 5432,
            "database": "myapp",
            "user": "user",
            "password": "password"
        },
        "dao": {}  # Зависимости инъектируются автоматически
    }
    
    app = AppWithDAO(components_config=config)
    
    try:
        # Запускаем приложение
        await app.start()
        print("App started")
        
        # Используем бизнес-логику
        result = await app.business_logic()
        print(f"Users: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Останавливаем приложение
        await app.stop()
        print("App stopped")


# ============ Пример 3: С правильными типами ============

class AppTyped(BaseApp):
    """Приложение с правильными типами."""
    
    pg = component(PG, config_key="pg")
    
    async def business_logic(self) -> List[Record]:
        """
        Бизнес-логика с правильными типами.
        
        Returns:
            Список записей из базы данных
        """
        # Используем типизированный доступ
        pool: Pool = self.pg.obj
        rows: List[Record] = await pool.fetch("SELECT 1")
        return rows
    
    async def _stop(self) -> None:
        """Останавливает приложение."""
        pass


async def example_typed_app():
    """Пример использования типизированного App."""
    print("\n=== Пример 3: Типизированный App ===")
    
    config = {
        "pg": {
            "host": "localhost",
            "port": 5432,
            "database": "myapp",
            "user": "user",
            "password": "password"
        }
    }
    
    app = AppTyped(components_config=config)
    
    try:
        await app.start()
        result = await app.business_logic()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await app.stop()


# ============ Запуск всех примеров ============

async def main():
    """Запускает все примеры."""
    print("=" * 60)
    print("Примеры использования App класса")
    print("=" * 60)
    
    # Запускаем примеры (закомментированы, т.к. требуют реальную БД)
    # await example_basic_app()
    # await example_app_with_dao()
    # await example_typed_app()
    
    print("\n⚠️  Примечание: Примеры закомментированы, т.к. требуют реальную базу данных.")
    print("Для запуска нужно:")
    print("1. Настроить подключение к PostgreSQL")
    print("2. Раскомментировать вызовы примеров")
    print("3. Запустить: python examples_user_app.py")


if __name__ == "__main__":
    asyncio.run(main())

