"""add call_duration_seconds to leads

Revision ID: 20260622_call_duration
Revises: 20260622_call_first_flow
Create Date: 2026-06-22 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260622_call_duration'
down_revision = '20260622_call_first_flow'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('leads', sa.Column('call_duration_seconds', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('leads', 'call_duration_seconds')
