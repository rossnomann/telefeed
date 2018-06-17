import functools
import itertools
import logging
import sys

from telefeed.models import Channel, Feed, Entry

logger = logging.getLogger(__name__)


class Cmd:
    PATTERN_ATTR = 'tg_cmd_pattern'

    def __init__(self, sa_engine, admin_user=None):
        self._sa_engine = sa_engine
        self._admin_user = str(admin_user) if admin_user else None

    def setup(self, bot, module=None):
        if not module:
            module = sys.modules[__name__]
        for i in dir(module):
            obj = getattr(module, i)
            pattern = getattr(obj, self.PATTERN_ATTR, None)
            if pattern is not None:
                bot.add_command(pattern, self._create(obj))

    def _create(self, func):
        @functools.wraps(func)
        async def decorator(chat, match):
            if not self._is_granted(chat.sender):
                logger.error('Access forbidden: %s', chat.sender)
                return
            args = [match.group(i) for i in range(1, match.lastindex + 1)] if match.lastindex else []
            async with self._sa_engine.acquire() as sa_conn:
                reply = await func(sa_conn, *args)
                if isinstance(reply, tuple):
                    reply, reply_options = reply
                else:
                    reply_options = {}
                if not isinstance(reply, list):
                    reply = [reply]
                for i in reply:
                    await chat.send_text(i, **reply_options)
        return decorator

    def _is_granted(self, sender):
        if not self._admin_user:
            return True
        if str(sender['id']) == self._admin_user:
            return True
        if not sender['username']:
            return False
        return sender['username'] == self._admin_user

    @classmethod
    def declare(cls, pattern):
        def decorator(func):
            setattr(func, cls.PATTERN_ATTR, pattern)
            return func
        return decorator


@Cmd.declare('listchannels')
async def list_channels(sa_conn):
    cm = Channel(sa_conn)
    items = await cm.get_list()
    if not items:
        return 'There are no channels to display'
    return '\n'.join('@{}'.format(i['name']) for i in items)


@Cmd.declare('addchannel ([\w]+)')
async def add_channel(sa_conn, name):
    name = _clean_channel_name(name)
    if not name:
        return 'Bad channel name'
    cm = Channel(sa_conn)
    obj = await cm.find_one(cm['name'] == name)
    if obj:
        return 'Channel already exists'
    await cm.create(name=name)
    return 'OK'


@Cmd.declare('delchannel ([\w]+)')
async def del_channel(sa_conn, name):
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


@Cmd.declare('listfeeds')
async def list_feeds(sa_conn):
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


@Cmd.declare('addfeed ([\w]+) (.+)')
async def add_feed(sa_conn, channel, url):
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


@Cmd.declare('delfeed ([\w]+) (.+)')
async def del_feed(sa_conn, channel, url):
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


def _clean_channel_name(name):
    if len(name) > 0 and name[0] == '@':
        name = name[1:]
    return name


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]
