from logging import getLogger
import asyncio
from typing import Any, Dict, Optional

from aiohttp import ClientSession

from adc_appkit import Component

logger = getLogger(__name__)


class HTTP(Component[ClientSession]):

    async def _start(self, **kwargs) -> ClientSession:
        return ClientSession(**kwargs)

    async def _stop(self):
        await self.obj.close()
