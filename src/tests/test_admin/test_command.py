import pytest

from telefeed.admin import handlers
from telefeed.admin.command import CommandHandler, generate_commands, generate_help


def test_generate_commands():
    commands = generate_commands(handlers)
    assert commands.pop('listchannels') == {
        'handler': handlers.list_channels,
        'args': [],
        'desc': 'show channels',
        'requires_sa': True
    }
    assert commands.pop('addchannel') == {
        'handler': handlers.add_channel,
        'args': [(0, 'name', True)],
        'desc': 'add channel',
        'requires_sa': True
    }
    assert commands.pop('delchannel') == {
        'handler': handlers.del_channel,
        'args': [(0, 'name', True)],
        'desc': 'delete channel',
        'requires_sa': True
    }
    assert commands.pop('listfeeds') == {
        'handler': handlers.list_feeds,
        'args': [],
        'desc': 'show feeds',
        'requires_sa': True
    }
    assert commands.pop('addfeed') == {
        'handler': handlers.add_feed,
        'args': [(0, 'channel', True), (1, 'url', True)],
        'desc': 'add feed to channel',
        'requires_sa': True
    }
    assert commands.pop('delfeed') == {
        'handler': handlers.del_feed,
        'args': [(0, 'channel', True), (1, 'url', True)],
        'desc': 'delete feed from channel',
        'requires_sa': True
    }


def test_generate_help():
    commands = generate_commands(handlers)
    help_message = generate_help(commands, completion=False)
    assert help_message == '\n'.join([
        '/start alias for /help',
        '/help show this message',
        '/addchannel <name> add channel',
        '/addfeed <channel> <url> add feed to channel',
        '/delchannel <name> delete channel',
        '/delfeed <channel> <url> delete feed from channel',
        '/listchannels show channels',
        '/listfeeds show feeds'
    ])
    completion_message = generate_help(commands, completion=True)
    assert completion_message == '\n'.join([
        'addchannel - add channel: <name>',
        'addfeed - add feed to channel: <channel> <url>',
        'delchannel - delete channel: <name>',
        'delfeed - delete feed from channel: <channel> <url>',
        'listchannels - show channels',
        'listfeeds - show feeds'
    ])


class SAEngineMock:
    def acquire(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        pass


class SaCommandHandlerMock:
    def __init__(self):
        self.calls = []

    async def __call__(self, sa_conn, x, y=None):
        self.calls.append((sa_conn, x, y))
        return 'test reply'


class CommandHandlerMock:
    def __init__(self):
        self.calls = 0

    async def __call__(self):
        self.calls += 1
        return self.calls


@pytest.mark.asyncio
async def test_handler():
    sa_engine = SAEngineMock()
    sa_command_handler = SaCommandHandlerMock()
    command_handler = CommandHandlerMock()
    commands = {
        'test': {
            'handler': sa_command_handler,
            'args': [(0, 'x', True), (1, 'y', False)],
            'desc': 'test command',
            'requires_sa': True
        },
        'test1': {
            'handler': command_handler,
            'args': [],
            'desc': 'test command 1',
            'requires_sa': False
        }
    }
    handler = CommandHandler(commands, sa_engine)
    assert (await handler.handle('"xxx')) == 'No closing quotation'
    assert (await handler.handle('')) == 'Empty command'
    assert (await handler.handle('/start')) == handler.help_message
    assert (await handler.handle('/help')) == handler.help_message
    assert (await handler.handle('/listcommands')) == handler.completion_message
    assert (await handler.handle('/start extra')) == 'Too many arguments'
    assert (await handler.handle('/help extra')) == 'Too many arguments'
    assert (await handler.handle('/listcommands extra')) == 'Too many arguments'
    assert (await handler.handle('/unknwon')) == 'Command not found'
    assert (await handler.handle('/test a b c')) == 'Too many arguments'
    assert (await handler.handle('/test')) == 'x is required'
    assert (await handler.handle('/test a')) == 'test reply'
    assert (await handler.handle('/test a b')) == 'test reply'
    assert sa_command_handler.calls == [(sa_engine, 'a', None), (sa_engine, 'a', 'b')]
    assert (await handler.handle('/test1')) == 1
    assert (await handler.handle('/test1 extra')) == 'Too many arguments'
    assert command_handler.calls == 1
