import asyncio
import logging

from datetime import datetime
from time import mktime

import feedparser

from telefeed import config
from telefeed.models import Feed, Entry


logger = logging.getLogger(__name__)


def parse_url(url):
    result = feedparser.parse(url)
    entries = result['entries']
    result = []
    for entry in entries:
        entry_date = None
        if 'updated_parsed' in entry:
            entry_date = entry['updated_parsed']
        elif 'published_parsed' in entry:
            entry_date = entry['published_parsed']
        if entry_date:
            entry_date = datetime.fromtimestamp(mktime(entry_date))
        result.append((entry['link'], entry.get('title', ''), entry_date))
    return result


class Parser:
    def __init__(self, loop, feed, entry):
        self.loop = loop
        self.feed = feed
        self.entry = entry

    async def _parse_url(self, url):
        return await self.loop.run_in_executor(None, parse_url, url)

    async def parse_feeds(self):
        feeds = await self.feed.find_oldest(config.PARSE_TIMEOUT)
        if not feeds:
            logger.info('No feeds found')
            return
        logger.info('Parsing feeds started')
        entries_count = 0
        for feed in feeds:
            logger.info('Parsing feed "%s"', feed['url'])
            try:
                entries = await self._parse_url(feed['url'])
            except Exception as exc:
                logger.exception('Failed to parse feed "%s"', feed['url'])
            else:
                for link, title, date in entries:
                    if not (await self.entry.is_exists(feed['id'], link)):
                        params = {'feed_id': feed['id'], 'title': title, 'link': link}
                        if date:
                            params['created_at'] = date
                        await self.entry.create(**params)
                        entries_count += 1
                await self.feed.mark_as_updated(feed['id'])
                logger.info('Parsing feed "%s" finished', feed['url'])
        logger.info('Parsing feeds finished (%d entries created)', entries_count)


async def run(loop, sa_engine):  # pragma: no cover
    async with sa_engine.acquire() as sa_conn:
        fm = Feed(sa_conn)
        em = Entry(sa_conn)
        parser = Parser(loop, fm, em)
        while True:
            await parser.parse_feeds()
            await asyncio.sleep(5)
