"""
Appkit - компонентная архитектура для Python приложений.

Это упрощенная и улучшенная версия архитектуры appkit.
"""

from adc_appkit.base_app import BaseApp
from adc_appkit.component_manager import (
    ComponentDescriptor,
    ComponentStrategy,
    component,
)
from adc_appkit.di_container import DIContainer
from adc_appkit.request_scope import RequestScope

__all__ = [
    "BaseApp",
    "ComponentDescriptor",
    "ComponentStrategy",
    "DIContainer",
    "RequestScope",
    "component",
]
