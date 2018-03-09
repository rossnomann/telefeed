import os

import pytest

from telefeed import config


def test_getenv():
    with pytest.raises(KeyError):
        config.getenv('unknown')
    assert config.getenv('unknown', required=False) is None
    os.environ['TELEFEED_UNKNOWN'] = ''
    try:
        with pytest.raises(ValueError):
            config.getenv('unknown')
    finally:
        os.environ.pop('TELEFEED_UNKNOWN')
