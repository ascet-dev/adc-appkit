from logging import getLogger
import asyncio
from typing import Any, Dict, Optional

from aiohttp import ClientSession

from adc_appkit.components.component import Component

logger = getLogger(__name__)


class HTTP(Component[ClientSession]):
    async def _start(self, **kwargs) -> ClientSession:
        return ClientSession(**kwargs)

    async def _stop(self) -> None:
        await self.obj.close()

    async def is_alive(self) -> bool:
        try:
            # Простая проверка - попытка создать запрос
            return not self.obj.closed
        except Exception:
            return False
