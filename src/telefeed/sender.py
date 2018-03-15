import asyncio
import logging
import html

from telefeed import config
from telefeed.models import Channel, Entry


logger = logging.getLogger(__name__)

SEND_TIMEOUT = 60


class Sender:
    def __init__(self, bot, channel, entry):
        self.bot = bot
        self.channel = channel
        self.entry = entry

    async def send_entries(self):
        logger.info('Sending entries...')
        for channel in (await self.channel.get_list()):
            channel_name = '@{}'.format(channel['name'])
            sent = []
            for entry in (await self.entry.get_new_for_channel(channel['id'])):
                try:
                    entry = dict(entry)
                    entry['title'] = html.escape(entry['title'], quote=False)
                    entry['title'] = entry['title'].replace('"', '&quot;')
                    entry['created_at'] = entry['created_at'].astimezone(config.TIMEZONE)
                    entry['created_at'] = entry['created_at'].strftime('%b %d, %Y / %H:%M')
                    msg = '<a href="{link}">{title}</a> ({created_at})'.format(**entry)
                    await self.bot.sendMessage(channel_name, msg, parse_mode='HTML')
                except Exception:
                    logger.exception('Failed to send entry %s to %s', entry['id'], channel_name)
                else:
                    sent.append(entry['id'])
            if sent:
                await self.entry.mark_as_sent(sent)
        logger.info('Sending entries done')


async def run(loop, sa_engine, bot):  # pragma: no cover
    async with sa_engine.acquire() as sa_conn:
        channel = Channel(sa_conn)
        entry = Entry(sa_conn)
        sender = Sender(bot, channel, entry)
        while True:
            await sender.send_entries()
            await asyncio.sleep(SEND_TIMEOUT)
