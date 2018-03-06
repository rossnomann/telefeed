import logging

from telefeed import config

logger = logging.getLogger(__name__)


def main():
    config.setup_logging()
    logger.info('Telefeed started')
