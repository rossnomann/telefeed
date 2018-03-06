"""empty message

Revision ID: e04dc703b258
Revises: b693807d3fb1
Create Date: 2018-03-06 23:23:14.614907

"""
import sqlalchemy as sa

from alembic import op


revision = 'e04dc703b258'
down_revision = 'b693807d3fb1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('feed', sa.Column('updated_at', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('feed', 'updated_at')
