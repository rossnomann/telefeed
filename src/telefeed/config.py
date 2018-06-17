import logging
import os
import sys

from pytz import timezone


def getenv(key, *, required=True):
    key = 'TELEFEED_{}'.format(key.upper())
    if key not in os.environ:
        if required:
            raise KeyError('Environment variable "{}" is not set'.format(key))
        return None
    value = os.environ[key]
    if required and not value:
        raise ValueError('Environment variable "{}" can not be empty'.format(key))
    return value


def setup_logging():
    level = logging.DEBUG if DEBUG else logging.WARNING

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    formatter = logging.Formatter('%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s')

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


DEBUG = getenv('debug', required=False) == 'true'
TOKEN = getenv('token')
SA_URL = getenv('sa_url')
PARSE_TIMEOUT = int(getenv('parse_timeout'))
TIMEZONE = timezone(getenv('timezone'))
ADMIN_USER_ID = getenv('admin_user_id')
PROXY = getenv('proxy', required=False)
