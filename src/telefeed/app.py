import asyncio
import logging

import aioreloader

from aiopg import sa
from aiotg import Bot

from telefeed import config, parser, sender
from telefeed.commands import Cmd

logger = logging.getLogger(__name__)


def main():
    config.setup_logging()
    logger.info('Telefeed started')
    loop = asyncio.get_event_loop()
    bot = Bot(config.TOKEN, proxy=config.PROXY)
    sa_engine = loop.run_until_complete(sa.create_engine(config.SA_URL, echo=config.DEBUG))
    cmd = Cmd(sa_engine, config.ADMIN_USER_ID)
    cmd.setup(bot)
    try:
        loop.create_task(bot.loop())
        loop.create_task(parser.run(loop, sa_engine))
        loop.create_task(sender.run(loop, sa_engine, bot))
        if config.DEBUG:
            aioreloader.start()
        loop.run_forever()
    finally:
        sa_engine.close()
        loop.run_until_complete(sa_engine.wait_closed())
