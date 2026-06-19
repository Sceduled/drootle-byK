"""add project fields to lead

Revision ID: 20260619_lead_projects
Revises: 20260619_projects_table
Create Date: 2026-06-19 19:35:05.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260619_lead_projects'
down_revision = '20260619_projects_table'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('leads', sa.Column('project_key', sa.Text(), nullable=True))
    op.add_column('leads', sa.Column('needs_project_assignment', sa.Boolean(), server_default=sa.text('false'), nullable=False))

def downgrade() -> None:
    op.drop_column('leads', 'needs_project_assignment')
    op.drop_column('leads', 'project_key')
