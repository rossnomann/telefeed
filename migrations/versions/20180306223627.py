"""add entry

Revision ID: b693807d3fb1
Revises: 6da59587d036
Create Date: 2018-03-06 22:36:27.290228

"""
import sqlalchemy as sa

from alembic import op


revision = 'b693807d3fb1'
down_revision = '6da59587d036'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'entry',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('feed_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('link', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('was_sent', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['feed_id'], ['feed.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('feed_id', 'title', 'link', name='entry_feed_title_link_uc')
    )


def downgrade():
    op.drop_table('entry')
