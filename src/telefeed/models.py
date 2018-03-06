from datetime import datetime

import sqlalchemy as sa


metadata = sa.MetaData()


class Base:
    table = None

    def __init__(self, conn):
        self.conn = conn

    def __getitem__(self, item):
        return self.table.c[item]

    async def find_one(self, *args):
        stmt = sa.select([self.table]).where(sa.and_(*args))
        result = await self.conn.execute(stmt)
        return await result.fetchone()

    async def create(self, **kwargs):
        stmt = self.table.insert().values(**kwargs)
        await self.conn.execute(stmt)

    async def update(self, *args, **kwargs):
        stmt = self.table.update().values(**kwargs)
        if args:
            stmt = stmt.where(sa.and_(*args))
        await self.conn.execute(stmt)

    async def delete(self, *args):
        stmt = self.table.delete()
        if args:
            stmt = stmt.where(sa.and_(*args))
        await self.conn.execute(stmt)


class Channel(Base):
    table = sa.Table(
        'channel',
        metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), unique=True, nullable=False),
    )


class Feed(Base):
    table = sa.Table(
        'feed',
        metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('channel_id', sa.ForeignKey('channel.id')),
        sa.Column('url', sa.String()),
        sa.Column('updated_at', sa.Integer(), default=0),
        sa.UniqueConstraint('channel_id', 'url', name='feed_channel_url_uc')
    )

    async def find_oldest(self, timeout):
        stmt = sa.select([self.table])
        stmt = stmt.where(now() - self['updated_at'] > timeout)
        stmt = stmt.order_by(self['updated_at'])
        result = await self.conn.execute(stmt)
        return await result.fetchall()

    async def mark_as_updated(self, feed_id):
        await self.update(self['id'] == feed_id, updated_at=now())


class Entry(Base):
    table = sa.Table(
        'entry',
        metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('feed_id', sa.ForeignKey('feed.id')),
        sa.Column('title', sa.String()),
        sa.Column('link', sa.String()),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('was_sent', sa.Boolean(), default=False),
        sa.UniqueConstraint('feed_id', 'title', 'link', name='entry_feed_title_link_uc')
    )

    async def is_exists(self, feed_id, title, link):
        stmt = sa.select([sa.func.count('*')])
        stmt = stmt.where(self['feed_id'] == feed_id)
        stmt = stmt.where(self['title'] == title)
        stmt = stmt.where(self['link'] == link)
        return (await self.conn.scalar(stmt)) > 0


def now():
    return sa.extract('epoch', sa.func.now())
