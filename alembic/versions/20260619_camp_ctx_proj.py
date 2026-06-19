"""add project_key to campaign context

Revision ID: 20260619_campaign_context_project
Revises: 20260619_lead_projects
Create Date: 2026-06-19 20:35:05.000000

"""
from alembic import op
import sqlalchemy as sa
import uuid


# revision identifiers, used by Alembic.
revision = '20260619_camp_ctx_proj'
down_revision = '20260619_lead_projects'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Add project_key column
    op.add_column('campaign_context', sa.Column('project_key', sa.Text(), nullable=True))
    
    # 2. Add foreign key constraint for project_key referencing projects table
    op.create_foreign_key('fk_campaign_context_project', 'campaign_context', 'projects', ['project_key'], ['project_key'])

    # 3. Drop the old unique constraint on context_key safely using Postgres IF EXISTS
    op.execute("ALTER TABLE campaign_context DROP CONSTRAINT IF EXISTS campaign_context_context_key_key")

    # 4. Create the new composite unique constraint
    op.create_unique_constraint('uq_project_context', 'campaign_context', ['project_key', 'context_key'])
    
    # 5. Set existing rows to have project_key 'whitefield_flat' if it exists.
    # Wait, the seed values from the previous migration need a project_key.
    # Let's update all existing contexts to belong to "whitefield_flat"
    op.execute("UPDATE campaign_context SET project_key = 'whitefield_flat'")


def downgrade() -> None:
    op.drop_constraint('uq_project_context', 'campaign_context', type_='unique')
    op.create_unique_constraint('campaign_context_context_key_key', 'campaign_context', ['context_key'])
    op.drop_constraint('fk_campaign_context_project', 'campaign_context', type_='foreignkey')
    op.drop_column('campaign_context', 'project_key')
