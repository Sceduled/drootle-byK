"""merge heads

Revision ID: 20260906_merge_heads
Revises: 20260617_080436, 20260622_call_duration, 5b6c7d8e9f0a
Create Date: 2026-09-06 20:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260906_merge_heads'
down_revision = ('20260617_080436', '20260622_call_duration', '5b6c7d8e9f0a')
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
