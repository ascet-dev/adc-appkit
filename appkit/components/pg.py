from logging import getLogger

from asyncpg import Pool

from appkit import Component
from pg_utils import create_db_pool

logger = getLogger(__name__)


class PG(Component[Pool]):
    async def _start(self, **kwargs) -> Pool:
        return await create_db_pool(**kwargs)

    async def _stop(self):
        await self.obj.close()

    async def is_alive(self) -> bool:
        return await self.obj.fetchval('SELECT 1')
