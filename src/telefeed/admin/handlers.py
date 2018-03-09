import itertools

from telefeed.models import Channel, Feed, Entry


def _clean_channel_name(name):
    if len(name) > 0 and name[0] == '@':
        name = name[1:]
    return name


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


async def list_channels(sa_conn):
    """listchannels - show channels"""
    cm = Channel(sa_conn)
    items = await cm.get_list()
    if not items:
        return 'There are no channels to display'
    return '\n'.join('@{}'.format(i['name']) for i in items)


async def add_channel(sa_conn, name):
    """addchannel - add channel"""
    name = _clean_channel_name(name)
    if not name:
        return 'Bad channel name'
    cm = Channel(sa_conn)
    await cm.create(name=name)
    return 'OK'


async def del_channel(sa_conn, name):
    """delchannel - delete channel"""
    name = _clean_channel_name(name)
    if not name:
        return 'Bad channel name'
    cm = Channel(sa_conn)
    obj = await cm.find_one(cm['name'] == name)
    if not obj:
        return 'Channel "{}" not found'.format(name)
    fm = Feed(sa_conn)
    em = Entry(sa_conn)
    await em.delete_for_channel(obj['id'])
    await fm.delete(fm['channel_id'] == obj['id'])
    await cm.delete(cm['id'] == obj['id'])
    return 'OK'


async def list_feeds(sa_conn):
    """listfeeds - show feeds"""
    fm = Feed(sa_conn)
    items = await fm.get_list()
    if items:
        text = []
        for channel, feeds in itertools.groupby(items, lambda x: x['channel']):
            text.append('<b>@{}</b>'.format(channel))
            for chunk in chunks(list(feeds), 10):
                text.append('\n'.join(feed['url'] for feed in chunk))
    else:
        text = 'There are no feeds to display'
    return text, {'parse_mode': 'HTML', 'disable_web_page_preview': True}


async def add_feed(sa_conn, channel, url):
    """addfeed - add feed to channel"""
    channel = _clean_channel_name(channel)
    if not channel:
        return 'Bad channel name'
    if not url:
        return 'Bad feed URL'
    cm = Channel(sa_conn)
    ch_obj = await cm.find_one(cm['name'] == channel)
    if not ch_obj:
        return 'Channel "{}" not found'.format(channel)
    fm = Feed(sa_conn)
    await fm.create(url=url, channel_id=ch_obj['id'])
    return 'OK'


async def del_feed(sa_conn, channel, url):
    """delfeed - delete feed from channel"""
    channel = _clean_channel_name(channel)
    if not channel:
        return 'Bad channel name'
    if not url:
        return 'Bad feed URL'
    cm = Channel(sa_conn)
    ch_obj = await cm.find_one(cm['name'] == channel)
    if not ch_obj:
        return 'Channel "{}" not found'.format(channel)
    fm = Feed(sa_conn)
    obj = await fm.find_one(fm['channel_id'] == ch_obj['id'], fm['url'] == url)
    if not obj:
        return 'Feed "{}" not found'.format(url)
    em = Entry(sa_conn)
    await em.delete(em['feed_id'] == obj['id'])
    await fm.delete(fm['id'] == obj['id'])
    return 'OK'
