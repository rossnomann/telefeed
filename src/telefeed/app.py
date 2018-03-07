import asyncio
import logging

import aioreloader

from aiopg import sa
from telepot.aio import Bot

from telefeed import admin, config, parser, sender

logger = logging.getLogger(__name__)


def main():
    config.setup_logging()
    logger.info('Telefeed started')
    loop = asyncio.get_event_loop()
    bot = Bot(config.TOKEN)
    sa_engine = loop.run_until_complete(sa.create_engine(config.SA_URL, echo=config.DEBUG))
    try:
        admin.start(loop, sa_engine, bot)
        loop.create_task(parser.run(loop, sa_engine))
        loop.create_task(sender.run(loop, sa_engine, bot))
        if config.DEBUG:
            aioreloader.start()
        loop.run_forever()
    finally:
        sa_engine.close()
        loop.run_until_complete(sa_engine.wait_closed())
