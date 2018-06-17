from datetime import datetime

import pytest

from telefeed.sender import Sender


class BotMock:
    def __init__(self):
        self.sent = []

    async def send_message(self, channel, msg, parse_mode):
        self.sent.append({'channel': channel, 'msg': msg, 'parse_mode': parse_mode})


class ChannelMock:
    def __init__(self, channels):
        self.channels = channels

    async def get_list(self):
        return self.channels


class EntryMock:
    def __init__(self, entries):
        self.entries = entries
        self.sent = []

    async def get_new_for_channel(self, channel_id):
        return self.entries[channel_id]

    async def mark_as_sent(self, entry):
        self.sent.append(entry)


@pytest.mark.asyncio
async def test_sender():
    bot = BotMock()
    channel = ChannelMock([
        {'name': 'channel1', 'id': 'channel1'},
        {'name': 'channel2', 'id': 'channel2'},
    ])
    entry = EntryMock({
        'channel1': [
            {
                'id': 'channel1entry1',
                'title': 'Test Channel 1',
                'link': 'http://test',
                'created_at': datetime(2012, 12, 21, 9, 0)
            }
        ],
        'channel2': [
            {
                'id': 'channel2entry1',
                'title': 'Test <"Channel"> \'2',
                'link': 'http://test',
                'created_at': datetime(2012, 12, 21, 9, 0)
            },
            {
                'id': 'invalid'
            }
        ]
    })
    sender = Sender(bot, channel, entry)
    await sender.send_entries()

    assert bot.sent == [
        {
            'channel': '@channel1',
            'msg': '<a href="http://test">Test Channel 1</a> (Dec 21, 2012 / 09:00 UTC)',
            'parse_mode': 'HTML'
        },
        {
            'channel': '@channel2',
            'msg': (
                '<a href="http://test">Test &lt;&quot;Channel&quot;&gt; \'2</a> '
                '(Dec 21, 2012 / 09:00 UTC)'
            ),
            'parse_mode': 'HTML'
        }
    ]

    assert entry.sent == ['channel1entry1', 'channel2entry1']
