from logging import getLogger
from typing import Any, Dict, Optional

from asyncpg import Pool

from adc_appkit.components.component import Component
from adc_aiopg import create_db_pool

logger = getLogger(__name__)


class PG(Component[Pool]):
    async def _start(self, **kwargs) -> Pool:
        return await create_db_pool(**kwargs)

    async def _stop(self) -> None:
        await self.obj.close()

    async def is_alive(self) -> bool:
        try:
            await self.obj.fetchval('SELECT 1')
            return True
        except Exception:
            return False
