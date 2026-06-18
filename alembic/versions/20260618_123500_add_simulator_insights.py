"""add simulator insights

Revision ID: 20260618_123500
Revises: 20260618_115200
Create Date: 2026-06-18 12:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260618_123500'
down_revision: Union[str, None] = '20260618_115200'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('simulation_sessions', sa.Column('lead_score', sa.Text(), nullable=True))
    op.add_column('simulation_sessions', sa.Column('ai_summary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('simulation_sessions', 'ai_summary')
    op.drop_column('simulation_sessions', 'lead_score')
