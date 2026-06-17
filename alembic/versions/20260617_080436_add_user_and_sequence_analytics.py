"""Add User and sequence analytics

Revision ID: 20260617_080436
Revises: 9fc6a7cf0890
Create Date: 2026-06-17 08:04:36

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260617_080436'
down_revision = '9fc6a7cf0890'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.Text(), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('role', sa.Text(), server_default='sales_rep', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # 2. Add assigned_to to leads
    op.add_column('leads', sa.Column('assigned_to', sa.Text(), nullable=True))
    op.create_index(op.f('ix_leads_assigned_to'), 'leads', ['assigned_to'], unique=False)

    # 3. Add sequence_step and replied to notifications_log
    op.add_column('notifications_log', sa.Column('sequence_step', sa.Text(), nullable=True))
    op.add_column('notifications_log', sa.Column('replied', sa.Boolean(), server_default='false', nullable=True))

def downgrade() -> None:
    # 3. Remove from notifications_log
    op.drop_column('notifications_log', 'replied')
    op.drop_column('notifications_log', 'sequence_step')

    # 2. Remove from leads
    op.drop_index(op.f('ix_leads_assigned_to'), table_name='leads')
    op.drop_column('leads', 'assigned_to')

    # 1. Drop users table
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')
