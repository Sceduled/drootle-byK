"""add call first flow fields

Revision ID: 20260622_call_first_flow
Revises: 20260619_camp_ctx_proj
Create Date: 2026-06-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '20260622_call_first_flow'
down_revision = '20260619_camp_ctx_proj'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('leads', sa.Column('call_attempted', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('leads', sa.Column('call_attempted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('leads', sa.Column('call_outcome', sa.Text(), nullable=True))
    op.add_column('leads', sa.Column('call_qualified', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('leads', sa.Column('call_partial_data', JSONB(), nullable=True))

def downgrade() -> None:
    op.drop_column('leads', 'call_partial_data')
    op.drop_column('leads', 'call_qualified')
    op.drop_column('leads', 'call_outcome')
    op.drop_column('leads', 'call_attempted_at')
    op.drop_column('leads', 'call_attempted')
