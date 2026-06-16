"""Add call_notes to lead

Revision ID: 9fc6a7cf0890
Revises: 0002
Create Date: 2026-06-16 10:02:11.211970

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9fc6a7cf0890'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('leads', sa.Column('call_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('leads', 'call_notes')
