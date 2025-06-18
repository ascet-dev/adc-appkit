from logging import getLogger
from typing import TypeVar

from appkit import Component
from pg_utils.repository import PostgresAccessLayer

logger = getLogger(__name__)

M = TypeVar('M', bound=PostgresAccessLayer)


class PGDataAccessLayer(Component[M]):
    async def _stop(self):
        return

    async def _start(self, **kwargs) -> M:
        return kwargs.pop('dbdao')(**kwargs)
