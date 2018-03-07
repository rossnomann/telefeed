from telepot.aio.loop import MessageLoop

from telefeed import config
from telefeed.admin import handlers
from telefeed.admin.command import CommandHandler, generate_commands
from telefeed.admin.message import MessageHandler


def start(loop, sa_engine, bot):
    commands = generate_commands(handlers)
    command_handler = CommandHandler(commands, sa_engine)
    message_handler = MessageHandler(config.ADMIN_USER_ID, bot, command_handler)
    message_loop = MessageLoop(bot, message_handler.handle)
    loop.create_task(message_loop.run_forever(allowed_updates=['message']))
