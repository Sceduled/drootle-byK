"""add_last_inbound_message_at

Revision ID: 5b6c7d8e9f0a
Revises: 9fc6a7cf0890
Create Date: 2026-09-06 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5b6c7d8e9f0a'
down_revision = '9fc6a7cf0890'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute('ALTER TABLE leads ADD COLUMN IF NOT EXISTS last_inbound_message_at TIMESTAMP WITH TIME ZONE')

def downgrade() -> None:
    op.execute('ALTER TABLE leads DROP COLUMN IF EXISTS last_inbound_message_at')
