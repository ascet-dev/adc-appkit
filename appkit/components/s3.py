from logging import getLogger

from appkit import Component
from s3_utils.client import S3Client

logger = getLogger(__name__)


class S3(Component[S3Client]):

    async def _start(self, **kwargs) -> S3Client:
        return await S3Client.create(**kwargs)

    async def _stop(self):
        await self.obj.close()

    async def is_alive(self) -> bool:
        return await self.obj.check_connection()
