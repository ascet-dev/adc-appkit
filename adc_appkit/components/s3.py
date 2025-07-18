from logging import getLogger
from typing import Any, Dict, Optional

from adc_appkit import Component
from adc_aios3.client import S3Client

logger = getLogger(__name__)


class S3(Component[S3Client]):

    async def _start(self, **kwargs) -> S3Client:
        return await S3Client.create(**kwargs)

    async def _stop(self):
        await self.obj.close()

    async def is_alive(self) -> bool:
        return await self.obj.check_connection()
