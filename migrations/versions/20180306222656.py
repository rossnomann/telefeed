"""add channel

Revision ID: be4e3f3a1709
Revises:
Create Date: 2018-03-06 22:26:56.157609

"""
import sqlalchemy as sa

from alembic import op


revision = 'be4e3f3a1709'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'channel',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )


def downgrade():
    op.drop_table('channel')
