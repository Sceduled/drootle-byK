"""projects table

Revision ID: 20260619_projects_table
Revises: 20260619_campaign_context
Create Date: 2026-06-19 19:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

# revision identifiers, used by Alembic.
revision = '20260619_projects_table'
down_revision = '20260619_campaign_context'
branch_labels = None
depends_on = None

def upgrade() -> None:
    projects_table = op.create_table(
        'projects',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('project_key', sa.Text(), nullable=False, unique=True),
        sa.Column('project_name', sa.Text(), nullable=False),
        sa.Column('area', sa.Text(), nullable=False),
        sa.Column('property_type', sa.Text(), nullable=False),
        sa.Column('bhk_or_size', sa.Text(), nullable=False),
        sa.Column('price_range', sa.Text(), nullable=False),
        sa.Column('key_features', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.bulk_insert(
        projects_table,
        [
            {
                "id": str(uuid.uuid4()),
                "project_key": "whitefield_flat",
                "project_name": "Prestige Raintree Park",
                "area": "Whitefield",
                "property_type": "flat",
                "bhk_or_size": "3, 4, 5 BHK",
                "price_range": "2Cr - 5Cr",
                "key_features": "Overlooks Varthur Lake, RERA approved, 21 acres, 18 towers, 1520 units, home loan assistance available",
                "active": True
            }
        ]
    )

def downgrade() -> None:
    op.drop_table('projects')
