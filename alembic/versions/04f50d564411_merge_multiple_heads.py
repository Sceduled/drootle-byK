"""merge multiple heads

Revision ID: 04f50d564411
Revises: 20260622_call_duration, 5b6c7d8e9f0a
Create Date: 2026-09-06 20:46:40.763646

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '04f50d564411'
down_revision = ('20260622_call_duration', '5b6c7d8e9f0a')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
