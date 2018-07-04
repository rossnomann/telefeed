import logging

from aiotg import Bot as BaseBot


logger = logging.getLogger(__name__)


class Bot(BaseBot):
    async def loop(self):
        self._running = True
        while self._running:
            try:
                updates = await self.api_call(
                    'getUpdates',
                    offset=self._offset + 1,
                    timeout=self.api_timeout
                )
            except Exception:
                logger.exception("Failed to get updates")
            else:
                self._process_updates(updates)
