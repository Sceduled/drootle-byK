"""campaign context table

Revision ID: 20260619_campaign_context
Revises: 20260619_sequence_timing
Create Date: 2026-06-19 18:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

# revision identifiers, used by Alembic.
revision = '20260619_campaign_context'
down_revision = '20260619_sequence_timing'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create the campaign_context table
    context_table = op.create_table(
        'campaign_context',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('context_key', sa.String(100), nullable=False, unique=True),
        sa.Column('context_value', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Seed the initial context values
    op.bulk_insert(
        context_table,
        [
            {
                "id": str(uuid.uuid4()),
                "context_key": "units_sold_this_week",
                "context_value": "12",
            },
            {
                "id": str(uuid.uuid4()),
                "context_key": "current_offer",
                "context_value": "Pre-launch pricing ends this month",
            },
            {
                "id": str(uuid.uuid4()),
                "context_key": "market_update",
                "context_value": "Whitefield prices up 8% this quarter",
            }
        ]
    )


def downgrade() -> None:
    op.drop_table('campaign_context')
