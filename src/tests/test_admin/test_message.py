import pytest

from telefeed.admin import message


class LoggerMock:
    def __init__(self):
        self.errors = []

    def error(self, msg, *args):
        self.errors.append(msg % args)

    def exception(self, msg, *args):
        self.errors.append(msg % args)

    def __enter__(self):
        self.errors = []
        return self.errors

    def __exit__(self, *exc_info):
        pass


class BotMock:
    def __init__(self):
        self.calls = []
        self.throw_exception = False

    async def sendMessage(self, chat_id, text, parse_mode=None):
        if self.throw_exception:
            raise Exception('An error has occurred')
        self.calls.append({'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode})


class CommandHandlerMock:
    def __init__(self):
        self.commands = []
        self.reply = None

    async def handle(self, command):
        self.commands.append(command)
        if self.reply is None:
            raise Exception('No reply')
        return self.reply


@pytest.mark.asyncio
async def test_handler():
    old_logger = message.logger
    logger = LoggerMock()
    message.logger = logger
    try:
        admin_user = 'testuser'
        bot = BotMock()
        command_handler = CommandHandlerMock()
        handler = message.MessageHandler(admin_user, bot, command_handler)

        # Bad user ID
        with logger as errors:
            msg = {'from': {'id': 'unexpected'}}
            await handler.handle(msg)
            assert errors == ['Access forbidden: %r' % msg['from']]

        # Bad user ID and Name
        with logger as errors:
            msg = {'from': {'id': 'unexpected', 'username': 'unexpected'}}
            await handler.handle(msg)
            assert errors == ['Access forbidden: %r' % msg['from']]

        # Unsupported flavor
        with logger as errors:
            msg = {'from': {'id': 1, 'username': admin_user}, 'result_id': 1}
            await handler.handle(msg)
            assert errors == ['Unsupported flavor: \'chosen_inline_result\'']

        # Unexpected chat type
        with logger as errors:
            msg = {
                'from': {'id': 1, 'username': admin_user},
                'message_id': 1,
                'text': 'test',
                'chat': {'type': 'test', 'id': 1}
            }
            await handler.handle(msg)
            assert errors == ['Got unexpected chat type: \'test\'']

        # Unsupported content type
        with logger as errors:
            msg = {
                'from': {'id': 1, 'username': admin_user},
                'message_id': 1,
                'audio': b'xxxx',
                'chat': {'type': 'private', 'id': 1}
            }
            await handler.handle(msg)
            assert errors == ['Unsupported content type: \'audio\'']

        # Failed to send message
        with logger as errors:
            bot.throw_exception = True
            msg = {
                'from': {'id': 1, 'username': admin_user},
                'message_id': 1,
                'text': 'test',
                'chat': {'type': 'private', 'id': 1}
            }
            await handler.handle(msg)
            assert errors[0].startswith('Failed to send message')
            bot.throw_exception = False

        # Command handler error
        with logger as errors:
            msg = {
                'from': {'id': 1, 'username': admin_user},
                'message_id': 1,
                'text': 'test',
                'chat': {'type': 'private', 'id': 1}
            }
            await handler.handle(msg)
            assert len(bot.calls) == 1
            bot_call = bot.calls[0]
            assert bot_call['chat_id'] == 1
            assert bot_call['text'].startswith('*An error has occurred while executing a command')
            assert bot_call['parse_mode'] == 'Markdown'
            assert not errors

        # Success
        with logger as errors:
            command_handler.reply = 'test reply'
            msg = {
                'from': {'id': 1, 'username': admin_user},
                'message_id': 1,
                'text': 'test',
                'chat': {'type': 'private', 'id': 1}
            }
            await handler.handle(msg)
            command_handler.reply = 'test reply', {'parse_mode': 'Markdown'}
            await handler.handle(msg)
            assert len(bot.calls) == 3
            bot_call = bot.calls[1]
            assert bot_call['chat_id'] == 1
            assert bot_call['text'] == 'test reply'
            assert bot_call['parse_mode'] is None
            bot_call = bot.calls[2]
            assert bot_call['chat_id'] == 1
            assert bot_call['text'] == 'test reply'
            assert bot_call['parse_mode'] == 'Markdown'
            assert not errors
    finally:
        message.logger = old_logger
