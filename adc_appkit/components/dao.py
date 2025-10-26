from logging import getLogger
from typing import TypeVar, Any, Dict, Optional

from adc_appkit.components.component import Component
from adc_aiopg.repository import PostgresAccessLayer

logger = getLogger(__name__)

M = TypeVar('M', bound=PostgresAccessLayer)


class PGDataAccessLayer(Component[M]):
    async def _start(self, **kwargs) -> M:
        dbdao = kwargs.pop('dbdao')
        return dbdao(**kwargs)

    async def _stop(self) -> None:
        return

    async def is_alive(self) -> bool:
        # DAO компонент обычно не требует отдельной проверки здоровья
        return True
