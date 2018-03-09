import logging
import traceback

import telepot


logger = logging.getLogger(__name__)


class MessageHandler:
    def __init__(self, admin_user, bot, command_handler):
        self.admin_user = admin_user
        self.bot = bot
        self.command_handler = command_handler

    async def handle(self, msg):
        from_id = str(msg['from']['id'])
        from_username = msg['from'].get('username')
        if not (from_id == self.admin_user or from_username == self.admin_user):
            logger.error('Access forbidden: %r', msg['from'])
            return

        flavor = telepot.flavor(msg)
        if flavor == 'chat':
            return await self._handle_chat(msg)

        logger.error('Unsupported flavor: %r', flavor)
        return

    async def _handle_chat(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg, 'chat')
        if chat_type != 'private':
            logger.error('Got unexpected chat type: %r', chat_type)
            return
        if content_type != 'text':
            logger.error('Unsupported content type: %r', content_type)
            return
        try:
            reply = await self.command_handler.handle(msg['text'])
        except Exception:
            msg = 'An error has occurred while executing a command'
            msg = '*{}:*\n```\n{}\n```'.format(msg, traceback.format_exc())
            await self._send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
        else:
            if isinstance(reply, tuple):
                reply, reply_options = reply
            else:
                reply_options = {}
            await self._send_message(chat_id=chat_id, text=reply, **reply_options)

    async def _send_message(self, chat_id, text, **kwargs):
        if not isinstance(text, list):
            text = [text]
        for i in text:
            try:
                await self.bot.sendMessage(chat_id=chat_id, text=i, **kwargs)
            except Exception:
                error_msg = 'Failed to send message: chat_id=%r text=%r kwargs=%r'
                logger.exception(error_msg, chat_id, i, kwargs)
