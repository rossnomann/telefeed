import re
import sys

from contextlib import contextmanager

import pytest

from telefeed import commands


class ConnectionMock:
    async def __aenter__(self):
        pass

    async def __aexit__(self, *args, **kwargs):
        pass


SA_CONN = ConnectionMock()


class EngineMock:
    def acquire(self):
        return SA_CONN


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
        old_models[k] = getattr(commands, k)
        setattr(commands, k, v)
    try:
        yield
    finally:
        for k, v in old_models.items():
            getattr(commands, k).reset()
            setattr(commands, k, v)


@pytest.mark.asyncio
async def test_list_channels():
    with mock_models():
        assert (await commands.list_channels(SA_CONN)) == 'There are no channels to display'
        ChannelMock.items = [{'name': 'test1'}, {'name': 'test2'}]
        assert (await commands.list_channels(SA_CONN)) == '@test1\n@test2'


@pytest.mark.asyncio
async def test_add_channel():
    with mock_models():
        assert (await commands.add_channel(SA_CONN, 'test1')) == 'OK'
        assert (await commands.add_channel(SA_CONN, '@test2')) == 'OK'
        assert (await commands.add_channel(SA_CONN, '@')) == 'Bad channel name'
        assert (await commands.add_channel(SA_CONN, '')) == 'Bad channel name'
        assert ChannelMock.created == ['test1', 'test2']

        old_find = ChannelMock.find_one

        async def new_find(*args):
            return True
        ChannelMock.find_one = new_find
        try:
            assert (await commands.add_channel(SA_CONN, 'test')) == 'Channel already exists'
        finally:
            ChannelMock.find_one = old_find


@pytest.mark.asyncio
async def test_del_channel():
    with mock_models():
        assert (await commands.del_channel(SA_CONN, '')) == 'Bad channel name'
        assert (await commands.del_channel(SA_CONN, '@')) == 'Bad channel name'
        assert (await commands.del_channel(SA_CONN, '@unknown')) == 'Channel "unknown" not found'
        ChannelMock.obj = {'id': 'test'}
        assert (await commands.del_channel(SA_CONN, '@test')) == 'OK'
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
        assert (await commands.list_feeds(SA_CONN)) == ('There are no feeds to display', opts)
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
        assert (await commands.list_feeds(SA_CONN)) == (expected, opts)


@pytest.mark.asyncio
async def test_add_feed():
    with mock_models():
        assert (await commands.add_feed(SA_CONN, '', '')) == 'Bad channel name'
        assert (await commands.add_feed(SA_CONN, '@', '')) == 'Bad channel name'
        assert (await commands.add_feed(SA_CONN, '@test', '')) == 'Bad feed URL'
        assert (await commands.add_feed(SA_CONN, '@x', 'url')) == 'Channel "x" not found'
        ChannelMock.obj = {'id': 'test'}
        assert (await commands.add_feed(SA_CONN, '@test', 'url')) == 'OK'
        assert FeedMock.created == [('test', 'url')]


@pytest.mark.asyncio
async def test_del_feed():
    with mock_models():
        assert (await commands.del_feed(SA_CONN, '', '')) == 'Bad channel name'
        assert (await commands.del_feed(SA_CONN, '@', '')) == 'Bad channel name'
        assert (await commands.del_feed(SA_CONN, '@test', '')) == 'Bad feed URL'
        assert (await commands.del_feed(SA_CONN, '@x', 'url')) == 'Channel "x" not found'
        ChannelMock.obj = {'id': 'testchannel'}
        assert (await commands.del_feed(SA_CONN, '@test', 'url')) == 'Feed "url" not found'
        FeedMock.obj = {'id': 'testfeed'}
        assert (await commands.del_feed(SA_CONN, '@test', 'url')) == 'OK'
        assert len(EntryMock.del_calls) == 1
        del_call = EntryMock.del_calls[0]
        assert len(del_call) == 1
        assert str(del_call[0]) == 'feed_id == testfeed'
        del_call = FeedMock.del_calls[0]
        assert len(del_call) == 1
        assert str(del_call[0]) == 'id == testfeed'


class BotMock:
    def __init__(self):
        self.commands = {}

    def add_command(self, pattern, handler):
        self.commands[pattern] = handler


class ChatMock:
    def __init__(self, sender):
        self.sender = sender
        self.sent = []

    async def send_text(self, text, **options):
        self.sent.append({'text': text, 'options': options})


@pytest.mark.asyncio
async def test_cmd():
    bot = BotMock()
    cmd = commands.Cmd(None, None)
    cmd.setup(bot)
    assert sorted(bot.commands.keys()) == [
        'addchannel ([\w]+)',
        'addfeed ([\w]+) (.+)',
        'delchannel ([\w]+)',
        'delfeed ([\w]+) (.+)',
        'listchannels',
        'listfeeds'
    ]

    bot = BotMock()
    admin_user = 'admin'
    cmd = commands.Cmd(EngineMock(), admin_user)
    cmd.setup(bot, sys.modules[__name__])

    admin_chat = ChatMock({'id': 1, 'username': admin_user})
    user_chat = ChatMock({'id': 2, 'username': 'test_user'})

    handler = bot.commands[mock_cmd.tg_cmd_pattern]
    await handler(admin_chat, re.match(mock_cmd.tg_cmd_pattern, 'test arg'))
    assert admin_chat.sent[0]['text'] == 'got arg'
    await handler(user_chat, None)
    assert not user_chat.sent

    handler = bot.commands[mock_cmd_opts.tg_cmd_pattern]
    opts_match = re.match(mock_cmd_opts.tg_cmd_pattern, 'testopts')
    await handler(admin_chat, opts_match)
    assert admin_chat.sent[1]['text'] == 'text'
    assert admin_chat.sent[1]['options'] == {'parse_mode': 'markdown'}

    cmd._admin_user = None
    await handler(user_chat, opts_match)
    assert len(user_chat.sent) == 1

    cmd._admin_user = '2'
    await handler(user_chat, opts_match)
    assert len(user_chat.sent) == 2

    cmd._admin_user = admin_user
    user_chat.sender['username'] = None
    await handler(user_chat, opts_match)
    assert len(user_chat.sent) == 2


@commands.Cmd.declare('test ([\w]+)')
async def mock_cmd(sa_conn, arg):
    return 'got {}'.format(arg)


@commands.Cmd.declare('testopts')
async def mock_cmd_opts(sa_conn):
    return 'text', {'parse_mode': 'markdown'}
