"""add feed

Revision ID: 6da59587d036
Revises: be4e3f3a1709
Create Date: 2018-03-06 22:33:52.973491

"""
import sqlalchemy as sa

from alembic import op


revision = '6da59587d036'
down_revision = 'be4e3f3a1709'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'feed',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=True),
        sa.Column('url', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['channel_id'], ['channel.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('channel_id', 'url', name='feed_channel_url_uc')
    )


def downgrade():
    op.drop_table('feed')
