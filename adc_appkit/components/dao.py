from logging import getLogger
from typing import TypeVar, Any, Dict, Optional

from adc_appkit import Component
from adc_aiopg.repository import PostgresAccessLayer

logger = getLogger(__name__)

M = TypeVar('M', bound=PostgresAccessLayer)


class PGDataAccessLayer(Component[M]):
    async def _stop(self):
        return

    async def _start(self, **kwargs) -> M:
        return kwargs.pop('dbdao')(**kwargs)
