import pytest

from telefeed.bot import BaseSession, Bot, Session


def test_bot():
    bot = Bot('test-token', proxy='socks5://user:pass@localhost:1234')
    assert isinstance(bot.session, Session)
    bot = Bot('test-token')
    assert isinstance(bot.session, BaseSession)


class RequestMock:
    def __init__(self):
        self.calls = []

    async def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))


@pytest.mark.asyncio
async def test_session():
    orig_request = BaseSession._request
    mock_request = RequestMock()
    BaseSession._request = mock_request
    proxy_auth = object()
    try:
        session = Session(proxy_auth=proxy_auth)
        await session._request()
    finally:
        BaseSession._request = orig_request
    assert mock_request.calls[0][1]['proxy_auth'] is proxy_auth
