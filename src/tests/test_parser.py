from collections import defaultdict

import pytest

from telefeed import config
from telefeed.parser import Parser


class FeedMock:
    def __init__(self, feeds):
        self.feeds = feeds
        self.updated = []

    async def find_oldest(self, timeout):
        assert timeout == config.PARSE_TIMEOUT
        return self.feeds

    async def mark_as_updated(self, feed_id):
        self.updated.append(feed_id)


class EntryMock:
    def __init__(self):
        self.__added = []
        self.entries = defaultdict(list)

    def _get_key(self, feed_id, title, link):
        return '-'.join(map(str, (feed_id, title, link)))

    async def is_exists(self, feed_id, title, link):
        return self._get_key(feed_id, title, link) in self.__added

    async def create(self, feed_id, title, link, created_at=None):
        key = self._get_key(feed_id, title, link)
        assert key not in self.__added
        self.__added.append(key)
        self.entries[feed_id].append({'title': title, 'link': link, 'created_at': created_at})


@pytest.mark.asyncio
async def test_parser(event_loop):
    feed = FeedMock([
        {
            'id': 1,
            'url': 'https://habrahabr.ru/rss/all/'
        },
        {
            'id': 2,
            'url': 'https://www.youtube.com/feeds/videos.xml?channel_id=UCnK9PxMozTYs8ELOvgMNKFA'
        }
    ])
    entry = EntryMock()
    parser = Parser(event_loop, feed, entry)
    await parser.parse_feeds()
    assert len(entry.entries[1]) > 0
    assert len(entry.entries[2]) > 0

    feed = FeedMock([])
    entry = EntryMock()
    parser = Parser(event_loop, feed, entry)
    await parser.parse_feeds()
    assert not entry.entries
