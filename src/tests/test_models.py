from datetime import datetime

import pytest

from aiopg import sa

from telefeed import models
from tests import SA_TEST_URL


@pytest.fixture
def sa_engine(event_loop):
    sa_engine = event_loop.run_until_complete(sa.create_engine(SA_TEST_URL))
    yield sa_engine
    sa_engine.close()
    event_loop.run_until_complete(sa_engine.wait_closed())


@pytest.mark.asyncio
async def test_channel(sa_engine):
    async with sa_engine.acquire() as sa_conn:
        channel = models.Channel(sa_conn)
        await channel.delete()

        channel_name = 'test create channel'
        await channel.create(name=channel_name)

        obj = await channel.find_one(channel['name'] == channel_name)
        assert obj['name'] == channel_name

        extra_channel_name = '01 test create extra channel'
        await channel.create(name=extra_channel_name)
        items = await channel.get_list()
        assert len(items) == 2
        assert items[0]['name'] == extra_channel_name
        assert items[1]['name'] == channel_name

        channel_name = channel_name + 'updated'
        await channel.update(channel['id'] == obj['id'], name=channel_name)

        old_id = obj['id']
        obj = await channel.find_one(channel['name'] == channel_name)
        assert obj['id'] == old_id
        assert obj['name'] == channel_name

        await channel.delete(channel['id'] == obj['id'])

        obj = await channel.find_one(channel['name'] == channel_name)
        assert not obj


@pytest.mark.asyncio
async def test_feed(sa_engine):
    async with sa_engine.acquire() as sa_conn:
        feed = models.Feed(sa_conn)
        await feed.delete()
        channel = models.Channel(sa_conn)
        await channel.delete()

        channel_id = await channel.create(name='channel for feeds test')
        feed1_url = 'http://feedforfeedstest1/'
        feed2_url = 'http://feedforfeedstest2/'
        feed1_date = datetime.utcnow().timestamp()
        feed2_date = datetime(2012, 12, 21, 20, 12).timestamp()
        await feed.create(channel_id=channel_id, url=feed1_url, updated_at=feed1_date)
        feed2_id = await feed.create(channel_id=channel_id, url=feed2_url, updated_at=feed2_date)
        items = await feed.get_list()
        assert len(items) == 2
        assert items[0]['url'] == feed1_url
        assert items[1]['url'] == feed2_url

        items = await feed.find_oldest(86400)
        assert len(items) == 1
        assert items[0]['id'] == feed2_id

        await feed.mark_as_updated(feed2_id)
        oldest = await feed.find_oldest(86400)
        assert not oldest


@pytest.mark.asyncio
async def test_entry(sa_engine):
    async with sa_engine.acquire() as sa_conn:
        entry = models.Entry(sa_conn)
        await entry.delete()
        feed = models.Feed(sa_conn)
        await feed.delete()
        channel = models.Channel(sa_conn)
        await channel.delete()

        channel_id = await channel.create(name='channel for entries test')
        extra_channel_id = await channel.create(name='extra channel for entries test')
        feed_id = await feed.create(channel_id=channel_id, url='http://testentries')
        extra_feed_id = await feed.create(channel_id=extra_channel_id, url='http://testentriesext')
        entry_id = await entry.create(feed_id=feed_id, title='entry', link='http://entry')
        extra_entry_id = await entry.create(feed_id=extra_feed_id, title='ext', link='http://ext')
        assert (await entry.is_exists(feed_id, 'entry', 'http://entry'))

        new_entries = await entry.get_new_for_channel(channel_id)
        assert len(new_entries) == 1
        assert new_entries[0]['id'] == entry_id

        await entry.mark_as_sent([entry_id])

        new_entries = await entry.get_new_for_channel(channel_id)
        assert not new_entries

        await entry.delete_for_channel(channel_id)
        assert not (await entry.find_one(entry['id'] == entry_id))
        assert (await entry.find_one(entry['id'] == extra_entry_id))['id'] == extra_entry_id

        await feed.delete(feed['id'] == feed_id)
        new_entries = await entry.get_new_for_channel(channel_id)
        assert not new_entries
