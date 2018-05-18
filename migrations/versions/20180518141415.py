"""update entry uc

Revision ID: af7ebbb3cfd8
Revises: e04dc703b258
Create Date: 2018-05-18 14:14:15.709186

"""
from alembic import op


revision = 'af7ebbb3cfd8'
down_revision = 'e04dc703b258'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint('entry_feed_link_uc', 'entry', ['feed_id', 'link'])
    op.drop_constraint('entry_feed_title_link_uc', 'entry', type_='unique')


def downgrade():
    op.create_unique_constraint('entry_feed_title_link_uc', 'entry', ['feed_id', 'title', 'link'])
    op.drop_constraint('entry_feed_link_uc', 'entry', type_='unique')
