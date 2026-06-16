"""Add ai_summary to lead

Revision ID: a1b2c3d4e5f6
Revises: 9fc6a7cf0890
Create Date: 2026-06-16 11:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '9fc6a7cf0890'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('leads', sa.Column('ai_summary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('leads', 'ai_summary')
