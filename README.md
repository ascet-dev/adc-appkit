# ADC AppKit

Библиотека для управления компонентами и состоянием приложения с поддержкой dependency injection, декларативного объявления компонентов и request scope.

## Основные возможности

- **Декларативное объявление компонентов** с IDE-подсказками
- **Dependency Injection** с автоматическим разрешением зависимостей
- **Две стратегии компонентов**: Singleton и Request
- **Request Scope** для управления жизненным циклом компонентов
- **Автоматическое управление состоянием** приложения
- **Healthcheck** для мониторинга состояния компонентов

## Архитектура

### Стратегии компонентов

- **SINGLETON**: создается один раз при старте приложения, закрывается при остановке
- **REQUEST**: создается при обращении, кэшируется в request scope, закрывается при выходе из scope

### Состояния компонентов

- **REGISTERED**: компонент зарегистрирован в контейнере
- **CONFIGURED**: компонент настроен конфигурацией
- **STARTED**: компонент запущен и готов к работе
- **STOPPED**: компонент остановлен
- **ERROR**: ошибка в работе компонента

## Быстрый старт

### Простое приложение

```python
import asyncio
from adc_appkit import BaseApp, component, ComponentStrategy
from adc_appkit.components.pg import PG
from adc_appkit.components.http import HTTP
from adc_appkit.components.s3 import S3

class MyApp(BaseApp):
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
        depends_on=[HTTP]
    )

    # S3 клиент - singleton
    s3 = component(
        S3,
        strategy=ComponentStrategy.SINGLETON,
        config_key="s3"
    )

    async def business_logic(self):
        # Использование компонентов вне scope
        print("PG pool:", self.pg)

        # Использование компонентов в request scope
        async with self.request_scope() as req:
            http_client = req.http
            print("HTTP client:", http_client)

# Конфигурация
config = {
    "http": {"timeout": 30},
    "pg": {"dsn": "postgresql://user:pass@localhost/db"},
    "s3": {"endpoint_url": "https://s3.amazonaws.com"}
}

app = MyApp(components_config=config)

async def main():
    await app.start()
    await app.business_logic()
    await app.stop()

asyncio.run(main())
```

### Сложное приложение с несколькими компонентами

```python
from adc_appkit import BaseApp, component, ComponentStrategy
from adc_appkit.components.pg import PG
from adc_appkit.components.http import HTTP

class ComplexApp(BaseApp):
    # Несколько HTTP клиентов
    main_http = component(
        HTTP,
        strategy=ComponentStrategy.REQUEST,
        config_key="main_http"
    )
    api_http = component(
        HTTP,
        strategy=ComponentStrategy.REQUEST,
        config_key="api_http"
    )

    # Несколько PG соединений
    main_pg = component(
        PG,
        strategy=ComponentStrategy.SINGLETON,
        config_key="main_pg",
        depends_on=["main_http"]
    )
    analytics_pg = component(
        PG,
        strategy=ComponentStrategy.SINGLETON,
        config_key="analytics_pg",
        depends_on=["api_http"]
    )

# Конфигурация
config = {
    "main_http": {"timeout": 5, "base_url": "https://api.main.com"},
    "api_http": {"timeout": 10, "base_url": "https://api.external.com"},
    "main_pg": {"dsn": "postgresql://user:pass@localhost/main_db"},
    "analytics_pg": {"dsn": "postgresql://user:pass@localhost/analytics_db"}
}

app = ComplexApp(components_config=config)
```

## Создание собственных компонентов

```python
from adc_appkit.components.component import Component
from typing import Any, Dict

class MyComponent(Component[MyObject]):
    async def _start(self, **kwargs) -> MyObject:
        # Инициализация компонента
        return MyObject(**kwargs)

    async def _stop(self) -> None:
        # Очистка ресурсов
        await self.obj.close()

    async def is_alive(self) -> bool:
        # Проверка состояния
        return await self.obj.is_healthy()
```

## Request Scope

Request scope позволяет управлять жизненным циклом REQUEST компонентов:

```python
async with app.request_scope() as req:
    # Все REQUEST компоненты создаются один раз на весь scope
    http1 = req.http
    http2 = req.http  # Тот же экземпляр

    # При выходе из scope все REQUEST компоненты автоматически закрываются
```

## Управление приложением

```python
# Запуск приложения
await app.start()

# Проверка состояния компонентов
health = await app.healthcheck()
print(health)  # {"pg": True, "s3": True, ...}

# Остановка приложения
await app.stop()
```

## Доступные компоненты

- **HTTP**: HTTP клиент на основе aiohttp (`adc_appkit.components.http.HTTP`)
- **PG**: PostgreSQL соединение на основе asyncpg (`adc_appkit.components.pg.PG`)
- **S3**: S3 клиент на основе boto3 (`adc_appkit.components.s3.S3`)
- **PGDataAccessLayer**: DAO слой для работы с PostgreSQL (`adc_appkit.components.dao.PGDataAccessLayer`)

## Запуск тестов

Для запуска тестов используйте uv:

```bash
# Установка зависимостей для разработки
uv sync --dev

# Запуск всех тестов
uv run pytest

# Запуск тестов с подробным выводом
uv run pytest -v

# Запуск конкретного теста
uv run pytest tests/test_architecture.py::test_simple_app_lifecycle
```

## Запуск примеров

Для запуска примеров использования:

```bash
# Простые примеры с мок-компонентами
uv run python examples/basic_examples.py

# Или запуск через модуль
uv run python -m examples.basic_examples
```

## Структура проекта

```
adc_appkit/
├── __init__.py              # Основные экспорты
├── base_app.py             # BaseApp класс
├── component_manager.py     # Управление компонентами
├── di_container.py         # DI контейнер
├── app.py                  # Примеры приложений
├── service.py              # Базовый Service класс
└── components/
    ├── component.py        # Базовый Component класс
    ├── pg.py              # PostgreSQL компонент
    ├── http.py            # HTTP клиент
    ├── s3.py              # S3 клиент
    └── dao.py             # DAO слой

tests/                      # Unit тесты
├── __init__.py
└── test_architecture.py   # Тесты архитектуры

examples/                   # Примеры использования
├── __init__.py
└── basic_examples.py      # Базовые примеры
```

## Разработка

Для разработки установите зависимости:

```bash
# Установка всех зависимостей
uv sync --dev

# Форматирование кода
uv run black adc_appkit tests examples

# Сортировка импортов
uv run isort adc_appkit tests examples

# Проверка типов
uv run mypy adc_appkit
```

## Установка

```bash
pip install adc-appkit
```

## Лицензия

Этот проект лицензирован под MIT License - см. файл LICENSE для деталей.
