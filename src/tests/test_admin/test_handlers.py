from contextlib import contextmanager

import pytest

from telefeed.admin import handlers


SA_CONN = object()


class ClauseMock:
    def __init__(self, lhs):
        self.lhs = lhs
        self.rhs = None

    def __str__(self):
        return '{} == {}'.format(self.lhs, self.rhs)

    def __eq__(self, other):
        if self.rhs:
            raise NotImplementedError()
        self.rhs = other
        return self


class ModelMock:
    obj = None
    find_calls = []
    del_calls = []

    def __init__(self, sa_conn):
        assert sa_conn is SA_CONN

    def __getitem__(self, item):
        return ClauseMock(item)

    @classmethod
    async def find_one(cls, *args):
        cls.find_calls.append(args)
        return cls.obj

    @classmethod
    async def delete(cls, *args):
        cls.del_calls.append(args)

    @classmethod
    def reset(cls):
        cls.obj = None
        cls.find_calls = []
        cls.del_calls = []


class ChannelMock(ModelMock):
    items = None
    created = []

    @classmethod
    async def create(cls, name):
        cls.created.append(name)

    @classmethod
    async def get_list(cls):
        return cls.items

    @classmethod
    def reset(cls):
        super().reset()
        cls.items = None
        cls.created = []


class FeedMock(ModelMock):
    items = None
    created = []

    @classmethod
    async def create(cls, channel_id, url):
        cls.created.append((channel_id, url))

    @classmethod
    async def get_list(cls):
        return cls.items

    @classmethod
    def reset(cls):
        super().reset()
        cls.items = None
        cls.created = []


class EntryMock(ModelMock):
    del_for_chan = []

    @classmethod
    async def delete_for_channel(cls, channel_id):
        cls.del_for_chan.append(channel_id)

    @classmethod
    def reset(cls):
        super().reset()
        cls.del_for_chan = []


@contextmanager
def mock_models():
    old_models = {}
    for k, v in [
        ('Channel', ChannelMock),
        ('Feed', FeedMock),
        ('Entry', EntryMock)
    ]:
        old_models[k] = getattr(handlers, k)
        setattr(handlers, k, v)
    try:
        yield
    finally:
        for k, v in old_models.items():
            getattr(handlers, k).reset()
            setattr(handlers, k, v)


@pytest.mark.asyncio
async def test_list_channels():
    with mock_models():
        assert (await handlers.list_channels(SA_CONN)) == 'There are no channels to display'
        ChannelMock.items = [{'name': 'test1'}, {'name': 'test2'}]
        assert (await handlers.list_channels(SA_CONN)) == '@test1\n@test2'


@pytest.mark.asyncio
async def test_add_channel():
    with mock_models():
        assert (await handlers.add_channel(SA_CONN, 'test1')) == 'OK'
        assert (await handlers.add_channel(SA_CONN, '@test2')) == 'OK'
        assert (await handlers.add_channel(SA_CONN, '@')) == 'Bad channel name'
        assert (await handlers.add_channel(SA_CONN, '')) == 'Bad channel name'
        assert ChannelMock.created == ['test1', 'test2']


@pytest.mark.asyncio
async def test_del_channel():
    with mock_models():
        assert (await handlers.del_channel(SA_CONN, '')) == 'Bad channel name'
        assert (await handlers.del_channel(SA_CONN, '@')) == 'Bad channel name'
        assert (await handlers.del_channel(SA_CONN, '@unknown')) == 'Channel "unknown" not found'
        ChannelMock.obj = {'id': 'test'}
        assert (await handlers.del_channel(SA_CONN, '@test')) == 'OK'
        assert len(ChannelMock.del_calls) == 1
        del_call = ChannelMock.del_calls[0]
        assert len(del_call) == 1
        assert str(del_call[0]) == 'id == test'
        assert EntryMock.del_for_chan == ['test']
        assert len(FeedMock.del_calls) == 1
        del_call = FeedMock.del_calls[0]
        assert len(del_call) == 1
        assert str(del_call[0]) == 'channel_id == test'


@pytest.mark.asyncio
async def test_list_feeds():
    with mock_models():
        opts = {'parse_mode': 'HTML', 'disable_web_page_preview': True}
        assert (await handlers.list_feeds(SA_CONN)) == ('There are no feeds to display', opts)
        FeedMock.items = [
            {'channel': 'ch1', 'url': 'url1'},
            {'channel': 'ch1', 'url': 'url2'},
            {'channel': 'ch1', 'url': 'url3'},
            {'channel': 'ch2', 'url': 'url1'},
            {'channel': 'ch2', 'url': 'url2'},
            {'channel': 'ch2', 'url': 'url3'}
        ]
        expected = [
            '<b>@ch1</b>', 'url1\nurl2\nurl3',
            '<b>@ch2</b>', 'url1\nurl2\nurl3',
        ]
        assert (await handlers.list_feeds(SA_CONN)) == (expected, opts)


@pytest.mark.asyncio
async def test_add_feed():
    with mock_models():
        assert (await handlers.add_feed(SA_CONN, '', '')) == 'Bad channel name'
        assert (await handlers.add_feed(SA_CONN, '@', '')) == 'Bad channel name'
        assert (await handlers.add_feed(SA_CONN, '@test', '')) == 'Bad feed URL'
        assert (await handlers.add_feed(SA_CONN, '@x', 'url')) == 'Channel "x" not found'
        ChannelMock.obj = {'id': 'test'}
        assert (await handlers.add_feed(SA_CONN, '@test', 'url')) == 'OK'
        assert FeedMock.created == [('test', 'url')]


@pytest.mark.asyncio
async def test_del_feed():
    with mock_models():
        assert (await handlers.del_feed(SA_CONN, '', '')) == 'Bad channel name'
        assert (await handlers.del_feed(SA_CONN, '@', '')) == 'Bad channel name'
        assert (await handlers.del_feed(SA_CONN, '@test', '')) == 'Bad feed URL'
        assert (await handlers.del_feed(SA_CONN, '@x', 'url')) == 'Channel "x" not found'
        ChannelMock.obj = {'id': 'testchannel'}
        assert (await handlers.del_feed(SA_CONN, '@test', 'url')) == 'Feed "url" not found'
        FeedMock.obj = {'id': 'testfeed'}
        assert (await handlers.del_feed(SA_CONN, '@test', 'url')) == 'OK'
        assert len(EntryMock.del_calls) == 1
        del_call = EntryMock.del_calls[0]
        assert len(del_call) == 1
        assert str(del_call[0]) == 'feed_id == testfeed'
        del_call = FeedMock.del_calls[0]
        assert len(del_call) == 1
        assert str(del_call[0]) == 'id == testfeed'
