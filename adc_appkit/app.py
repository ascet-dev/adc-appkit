"""
Примеры использования ADC AppKit.

Этот модуль содержит примеры создания приложений с использованием
декларативных компонентов, DI контейнера и request scope.
"""

from adc_appkit.base_app import BaseApp
from adc_appkit.component_manager import component, ComponentStrategy
from adc_appkit.components.pg import PG
from adc_appkit.components.http import HTTP
from adc_appkit.components.s3 import S3
from adc_appkit.components.dao import PGDataAccessLayer


# ======================= Пример простого приложения =======================

class SimpleApp(BaseApp):
    """Пример простого приложения с базовыми компонентами."""
    
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
    
    # DAO слой - singleton
    dao = component(
        PGDataAccessLayer,
        strategy=ComponentStrategy.SINGLETON,
        config_key="dao",
        depends_on=["pg"]
    )


# ======================= Пример сложного приложения =======================

class ExternalAPI(HTTP):
    """Кастомный HTTP клиент для внешнего API."""
    
    async def call_api(self, endpoint: str) -> str:
        """Вызов внешнего API."""
        # Здесь была бы реальная логика вызова API
        return f"API call to {endpoint}"


class ComplexApp(BaseApp):
    """Пример сложного приложения с несколькими компонентами одного типа."""
    
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
